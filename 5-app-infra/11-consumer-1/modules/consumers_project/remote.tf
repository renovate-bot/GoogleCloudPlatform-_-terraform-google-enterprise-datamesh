/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

locals {
  projects_backend_bucket = data.terraform_remote_state.bootstrap.outputs.projects_gcs_bucket_tfstate
  consumer_project        = data.terraform_remote_state.business_unit_env.outputs.consumer_projects[var.consumer_name].project_id
  bigquery_key_name       = data.terraform_remote_state.business_unit_env.outputs.consumer_projects_kms[var.consumer_name][var.keyring_region].id
}

data "terraform_remote_state" "bootstrap" {
  backend = "gcs"

  config = {
    bucket = var.remote_state_bucket
    prefix = "terraform/bootstrap/state"
  }
}

data "terraform_remote_state" "business_unit_env" {
  backend = "gcs"

  config = {
    bucket = local.projects_backend_bucket
    prefix = "terraform/projects/${var.business_unit}/${var.env}"
  }
}
