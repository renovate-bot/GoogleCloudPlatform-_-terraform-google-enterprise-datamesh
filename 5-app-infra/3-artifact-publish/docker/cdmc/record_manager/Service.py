import sys, json
import datetime, time
import requests
import os
import google.auth
import google.oauth2.id_token
import google.auth.transport.requests
from google.cloud import storage
from google.cloud import datacatalog
from google.cloud.datacatalog_v1 import types
from google.cloud import bigquery
from google.auth.transport.requests import Request
from google.cloud.exceptions import NotFound

class Service:

    def __init__(self):
        pass

    def search_catalog(self):
    
        retention_records = [] # collect all the tables to be processed along with their retention details
        
        scope = datacatalog.SearchCatalogRequest.Scope()
         
        for project in self.projects_in_scope:
            print('Info: project ' + project + ' is in scope')
            
            scope.include_project_ids.append(project)
        
        request = datacatalog.SearchCatalogRequest()
        request.scope = scope
        
        query = 'tag:' + self.template_project + '.' + self.template_id + '.' + self.retention_period_field
        
        dataset_index = 0
        
        for dataset_in_scope in self.datasets_in_scope:
            print('Info: dataset_in_scope: ' + dataset_in_scope)
            
            if dataset_index == 0:
                query += ' and parent:' + dataset_in_scope
            else:
                query += ' or parent:' + dataset_in_scope
                
            dataset_index += 1
        
        print('Info: using query: ' + query)
        request.query = query
        request.page_size = 1
    
        for result in self.dc_client.search_catalog(request):

            if result.integrated_system != types.IntegratedSystem.BIGQUERY:
                continue
            
            #print('Info: found linked resource', result.linked_resource)
                
            fqt = result.linked_resource.replace('//bigquery.googleapis.com/projects/', '').replace('/datasets/', '.').replace('/tables/', '.')
            project = fqt.split('.')[0]
            dataset = fqt.split('.')[1]
            table = fqt.split('.')[2]
            
            print('Info: found tagged table: ' + table)
            #print('result.linked_resource:', result.linked_resource)
                
            request = datacatalog.LookupEntryRequest()
            request.linked_resource=result.linked_resource
            entry = self.dc_client.lookup_entry(request)
            
            if entry.bigquery_table_spec.table_source_type != types.TableSourceType.BIGQUERY_TABLE:
                continue
            
            #print('entry:', entry)
            
            create_date = entry.source_system_timestamps.create_time.strftime("%Y-%m-%d")
            year = int(create_date.split('-')[0])
            month = int(create_date.split('-')[1])
            day = int(create_date.split('-')[2])
            
            tag_list = self.dc_client.list_tags(parent=entry.name, timeout=120)
        
            for tag in tag_list:
                
                #print('Info: found tag: ', tag)
                
                if tag.template == 'projects/{0}/locations/{1}/tagTemplates/{2}'.format(self.template_project, self.template_region, self.template_id):
                    
                    if self.retention_period_field in tag.fields:
                        field = tag.fields[self.retention_period_field]
                        retention_period_value = field.double_value
     
                    if self.expiration_action_field in tag.fields:
                        field = tag.fields[self.expiration_action_field]
                        if field.enum_value:
                            expiration_action_value = field.enum_value.display_name
                        else:
                            expiration_action_value = None
                    
                    if retention_period_value >= -1 and expiration_action_value:
                        record = {"project": project, "dataset": dataset, "table": table, "year": year, "month": month, "day": day, \
                                  "retention_period": retention_period_value, "expiration_action": expiration_action_value}
                        retention_records.append(record)
                    break
        
        return retention_records                      


    def create_snapshots(self, retention_records):
            
        for record in retention_records:

            if record['expiration_action'] != 'Purge':
                continue
        
            snapshot_name = record['dataset'] + '_' + record['table']
            snapshot_table = self.snapshot_project + '.' + self.snapshot_dataset + '.' + snapshot_name
            snapshot_expiration = record['retention_period'] + self.snapshot_retention_period + 1
            
            create_date = datetime.datetime(record['year'], record['month'], record['day'])
            snapshot_expiration = create_date + datetime.timedelta(days=snapshot_expiration)
            
            if record['retention_period'] == -1:
                retention_period = 0
            else:
                retention_period = record['retention_period']
                
            table_expiration = create_date + datetime.timedelta(days=retention_period)

            if table_expiration.date() <= datetime.date.today() and snapshot_expiration.date() > datetime.date.today():
                
                ddl = ('create snapshot table ' + snapshot_table
                        + ' clone ' + record['project'] + '.' + record['dataset'] + '.' + record['table'] 
                        + ' options ('
                        + ' expiration_timestamp = timestamp "' + snapshot_expiration.strftime("%Y-%m-%d") + '");') 

                try:

                    if self.mode == 'apply':
                    
                        
                        try:
                            self.bq_client.get_table(snapshot_table)  
                            self.bq_client.delete_table(snapshot_table)
                            print('Info: deleted snapshot table ' + snapshot_table) 
                            
                        except NotFound:
                            print("Snapshot table {} not found, skipping delete.".format(snapshot_table))
                        
                        print('Info: using ddl to create snapshot table: ' + ddl)    
                        query_job = self.bq_client.query(ddl).result()
                        print('Info: created snapshot table ' + snapshot_table)
                    
                    else:
                        # validate mode
                        print('Info: create snapshot table ' + snapshot_table)
                    
                except Exception as e:
                    print('Error occurred in create_snapshots. Error message: ' + str(e)) 
            
            else:
                print('skipping snapshot table creation for table ', record['table']) 


    def expire_tables(self, retention_records):
    
        for record in retention_records:
        
            if record['expiration_action'] != 'Purge':
                continue
        
            table_id = record['project'] + '.' + record['dataset'] + '.' + record['table']
            table_ref = bigquery.Table.from_string(table_id)
            table = self.bq_client.get_table(table_ref)
        
            create_date = datetime.datetime(record['year'], record['month'], record['day'])
            table_expiration = create_date + datetime.timedelta(days=record['retention_period']+1)
            
            try:
                                
                if self.mode == 'apply':

                    if table_expiration.date() > datetime.date.today():
                        table.expires = table_expiration
                        table = self.bq_client.update_table(table, ["expires"])
                        print('Info: set expiration on ' + table_id + ' to ' + table_expiration.strftime("%Y-%m-%d"))
                    else:
                        self.bq_client.delete_table(table_id, not_found_ok=True)  
                        print("Info: deleted table '{}'.".format(table_id))
                else:
                    # validate mode
                    print('Info: purge or expire table ' + table_id + ' on ' + table_expiration.strftime("%Y-%m-%d"))
                    
            
            except Exception as e:
                print('Error occurred while either setting expiration or purging table ' + table_id + '. Error message:' + str(e))  
    
    
    def archive_tables(self, retention_records):
        
        for record in retention_records:
        
            if record['expiration_action'] != 'Archive':
                continue
            
            create_date = datetime.datetime(record['year'], record['month'], record['day'])
            expiration = create_date + datetime.timedelta(days=record['retention_period']+1)
            
            if expiration.date() <= datetime.date.today():
                 
                 table_id = record['project'] + '.' + record['dataset'] + '.' + record['table']
                 
                 try:
                     
                     success, export_file = self.export_table(record['project'], record['dataset'], record['table'], table_id)
                     
                     if success == False:
                         print('Error: Exporting table failed, table', table_id, ' has not been archived.')
                         return
                         
                     external_table = record['dataset'] + '_' + record['table']
                     self.create_biglake_table(record['dataset'], record['table'], external_table, export_file)
                     self.copy_tags(record['project'], record['dataset'], record['table'], self.archives_project, self.archives_dataset,\
                                    external_table)
                     
                     print('Info: archive ' + table_id)
                     
                     # delete the archived table
                     if self.mode == 'apply':
                         self.bq_client.delete_table(table_id, not_found_ok=True)
                         print('Info: table ' + table_id + ' has been archived.')
                 
                 except Exception as e:
                     print('Error occurred while archiving table ' + table_id + '. Error message: ' + str(e))
    
    
    def export_table(self, project, dataset, table, table_id):
        
        success = True
        config = bigquery.job.ExtractJobConfig()
        config.destination_format = self.export_format
        
        table_ref = bigquery.Table.from_string(table_id)
        
        file_path = 'gs://' + self.archives_bucket + '/' + project + '/' + dataset + '/' + table + '.' + self.export_format
        print('Info: export ' + table_id + ' to ' + file_path)

        try:
            
            if self.mode == 'apply':
                job = self.bq_client.extract_table(source=table_ref, destination_uris=file_path, job_config=config)
                result = job.result()
                print('Info: created external file: ' + file_path)
                
        except Exception as e:
            print('Error occurred while exporting the table: ' + str(e))
            success = False
            
        return success, file_path
        
    
    def create_biglake_table(self, dataset, table, external_table, export_file):
        
        ddl = ('create or replace external table `' + self.archives_project + '.' + self.archives_dataset + '.' + external_table + '` '
              + 'with connection `' + self.remote_connection + '` '
              + 'options ( '
              + 'format = "' + self.export_format + '", '
              + 'uris = ["' + export_file + '"]);')
        
        print('Info: create biglake table using DDL: ' + ddl)
         
        try:
            
            if self.mode == 'apply':
                self.bq_client.query(ddl).result() 
                print('Info: created biglake table ' + external_table)
            
        except Exception as e: 
            print('Error occurred during create biglake table: ' + str(e))


    def get_oauth_token(self):
        # Get the default credentials for the service account running in Cloud Run
        credentials, project = google.auth.default()
        
        # Refresh the credentials to ensure they're valid and up-to-date
        credentials.refresh(Request())
        
        # Return the OAuth access token
        return credentials.token
    
    def get_bearer_token(self):
        # Get the default credentials for the service account running in Cloud Run
        auth_req = google.auth.transport.requests.Request()
        id_token = google.oauth2.id_token.fetch_id_token(auth_req, self.tag_engine_endpoint)
        
        # Return the OAuth access token
        return 'Bearer ' + id_token
    def copy_tags(self, source_project, source_dataset, source_table, target_project, target_dataset, target_table):
        
        oauth_token = self.get_oauth_token()
        bearer_token = self.get_bearer_token()

        headers = {'Authorization': bearer_token, "oauth_token": oauth_token}

        url = self.tag_engine_endpoint + '/copy_tags'
        payload = json.dumps({'source_project': source_project, 'source_dataset': source_dataset, 'source_table': source_table, 
                              'target_project': target_project, 'target_dataset': target_dataset, 'target_table': target_table})

        print('Info: copy tags using params: ' + str(payload))
        
        try:
            
            if self.mode == 'apply':
                res = requests.post(url, data=payload, headers=headers).json()
                print('Info: copy tags response: ' + str(res))
        
        except Exception as e: 
            print('Error occurred during copy_tags ' + str(e))    
        

    def get_param_file(self, file_path):
    
        file_path = file_path.replace('gs://', '')
        bucket = file_path.split('/')[0]
        file_name = file_path.replace(bucket + '/', '')
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(bucket)
        blob = bucket.get_blob(file_name)
        blob_data = blob.download_as_string()
        json_input = json.loads(blob_data) 
        return json_input


    def run_service(self, file_path):
        
        json_input = s.get_param_file(file_path)
        
        if not json_input:
            print('Missing json parameters.')
            sys.exit()
        
        if 'template_id' not in json_input:
            print('Missing template_id parameter.')
            sys.exit()
        else:   
            self.template_id = json_input['template_id']
            print('template_id: ', self.template_id)
    
        if 'template_project' not in json_input:
            print('Missing template_project parameter.')
            sys.exit()
        else:   
            self.template_project = json_input['template_project']
    
        if 'template_region' not in json_input:
            print('Missing template_region parameter.')
            sys.exit()
        else:   
            self.template_region = json_input['template_region']

        if 'retention_period_field' not in json_input:
            print('Missing retention_period_field parameter.')
            sys.exit()
        else:   
            self.retention_period_field = json_input['retention_period_field']

        if 'expiration_action_field' not in json_input:
            print('Missing expiration_action_field parameter.')
            sys.exit()
        else:   
            self.expiration_action_field = json_input['expiration_action_field']

        if 'projects_in_scope' not in json_input:
            print('Missing projects_in_scope parameter.')
            sys.exit()
        else:   
            self.projects_in_scope = json_input['projects_in_scope']
            
        if 'datasets_in_scope' in json_input:
            self.datasets_in_scope = json_input['datasets_in_scope']
            print('Info: datasets_in_scope set to:', self.datasets_in_scope) 
        else:   
            self.datasets_in_scope = []
            print('Info: datasets_in_scope is empty.')    

        if 'bigquery_region' not in json_input:
            print('Missing bigquery_region parameter.')
            sys.exit()
        else:   
            self.bigquery_region = json_input['bigquery_region']

        if 'snapshot_project' not in json_input:
            print('Missing snapshot_project parameter.')
            sys.exit()
        else:   
            self.snapshot_project = json_input['snapshot_project']

        if 'snapshot_dataset' not in json_input:
            print('Missing snapshot_dataset parameter.')
            sys.exit()
        else:   
            self.snapshot_dataset = json_input['snapshot_dataset']

        if 'snapshot_retention_period' not in json_input:
            print('Missing snapshot_retention_period parameter.')
            sys.exit()
        else:   
            self.snapshot_retention_period = json_input['snapshot_retention_period']

        if 'archives_bucket' not in json_input:
            print('Missing archives_bucket parameter.')
            sys.exit()
        else:   
            self.archives_bucket = json_input['archives_bucket']

        if 'export_format' not in json_input:
            print('Missing export_format parameter.')
            sys.exit()
        else:   
            self.export_format = json_input['export_format']

        if 'archives_project' not in json_input:
            print('Missing archives_project parameter.')
            sys.exit()
        else:   
            self.archives_project = json_input['archives_project']
        
        if 'archives_dataset' not in json_input:
            print('Missing archives_dataset parameter.')
            sys.exit()
        else:   
            self.archives_dataset = json_input['archives_dataset']

        if 'remote_connection' not in json_input:
            print('Missing remote_connection parameter.')
            sys.exit()
        else:   
            self.remote_connection = json_input['remote_connection']
        
        if 'tag_engine_endpoint' not in json_input:
            print('Missing tag_engine_endpoint parameter.')
            sys.exit()
        else:   
            self.tag_engine_endpoint = json_input['tag_engine_endpoint']
       
        if 'mode' not in json_input:
            print('Missing mode parameter.')
            sys.exit()
        else:   
            if json_input['mode'] != 'validate' and json_input['mode'] != 'apply':
                print('Invalid mode parameter. Must be equal to "validate" or "apply"')
                sys.exit()
            self.mode = json_input['mode']

        # create clients     
        self.dc_client = datacatalog.DataCatalogClient()
        self.bq_client = bigquery.Client(location=self.bigquery_region)
        
        print('Info: running in', self.mode, 'mode.')
        print(f'Info Bearer Token: {self.get_bearer_token()}')
        print(f'Info OAuth Token: {self.get_oauth_token()}')
        # search catalog
        retention_records = s.search_catalog()
        print('Info: found retention records in the catalog:', retention_records)
    
        # process purge actions
        s.create_snapshots(retention_records)
        s.expire_tables(retention_records)
    
        # process archive actions
        s.archive_tables(retention_records)
        

if __name__ == '__main__':
        
    if os.environ.get('PARAM_FILE') is None:
        print('Error: PARAM_FILE environment variable is required for running Record Manager. Needs to be equal to a GCS path starting with gs://')
        sys.exit()
    else:
        param_file = os.environ.get('PARAM_FILE')
        print('Info: param_file:', param_file)
   
    s = Service()
    s.run_service(param_file)
     