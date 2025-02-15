/**
 * Copyright 2021 Google LLC
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

env      = "nonproduction"
region   = "us-central1"
env_code = "n"

dataflow_template_jobs = {
  "pubsub_to_bq" = {
    "image_name"        = "samples/pubsub_to_bq_deidentification:nonproduction"
    "template_filename" = "pubsub_to_bq_deidentification-nonproduction.json"
    "additional_parameters" = {
      batch_size = 1000
    }
  },
  "gcs_to_bq" = {
    "image_name"        = "samples/gcs_to_bq_deidentification:nonproduction"
    "template_filename" = "gcs_to_bq_deidentification-nonproduction.json"
    "additional_parameters" = {
      min_batch_size = 10
      max_batch_size = 1000
    }
    "csv_file_names" = [
      "sample-100-encrypted.csv"
    ]
  }
}
