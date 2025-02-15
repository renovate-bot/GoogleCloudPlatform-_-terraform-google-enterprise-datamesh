#! /bin/bash
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 the "License";
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Passed parameters
export PROJECT_ID_DATA=$1
export PROJECT_ID_GOV=$2
export REGION=$3
export DATASET=$4
export SOURCE_DATASET_ID=$5
export TABLES=$6

# Required for gcloud
export GCLOUD_PROJECT=$PROJECT_ID_GOV

# Check if values are provided
if [ -z "$4" ]; then
    echo -e "\n\nYou have to provide the following parameters:"
    echo -e "\t1: project_id where the data resides"
    echo -e "\t2: project_id of the data governance, where DQ runs "
    echo -e "\t3: region where DQ runs "
    echo -e "\t4: dataset used to store the DQ results"
    echo -e "\t5: source dataset used to analyse the data"
    echo -e "\t6: tables to be analysed"
    exit
fi

echo -e "\n\nRunning with following values:"
echo -e "\tPROJECT_ID_DATA       : $PROJECT_ID_DATA"
echo -e "\tPROJECT_ID_GOV   : $PROJECT_ID_GOV"
echo -e "\tREGION           : $REGION"
echo -e "\tDATASET          : $DATASET"
echo -e "\tSOURCE_DATASET_ID: $SOURCE_DATASET_ID"
echo -e "\tTABLES           :$TABLES"

# Substitute the project variable in the configs
# declare -a FILES="(cc_data)"

IFS=',' read -r -a FILES <<< "$TABLES"
for f in "${FILES[@]}"
do
    :
    sed -i "s/PROJECT_ID_DATA/$PROJECT_ID_DATA/g" configs/${f}.yml
    sed -i "s/SOURCE_BIGQUERY_DATASET_ID/$SOURCE_DATASET_ID/g" configs/${f}.yml
done

# Remove files in configs directory that aren't in FILES array or "common.yml"
for file in configs/*.yml; do
    filename=$(basename "$file" .yml)
    [[ "$filename" != "common" && ! " ${FILES[*]} " =~ " $filename " ]] && rm "$file"
done

## Call Data Quality
python3 clouddq_executable.zip \
    ALL \
    configs \
    --gcp_project_id=${PROJECT_ID_GOV} \
    --gcp_bq_dataset_id=${DATASET} \
    --gcp_region_id=${REGION} \
    --target_bigquery_summary_table=${PROJECT_ID_GOV}.${DATASET}.results
