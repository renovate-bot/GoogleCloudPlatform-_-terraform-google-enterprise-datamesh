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

data "google_project" "project" {
  project_id = var.project_id
}

data "google_kms_key_ring" "kms" {
  name     = var.keyring_name
  location = var.region
  project  = var.kms_project_id
}

data "google_kms_crypto_key" "data_ingestion_key" {
  name     = "data_ingestion_key_${var.business_code}_${var.domain_name}_${var.environment}"
  key_ring = data.google_kms_key_ring.kms.id
}
