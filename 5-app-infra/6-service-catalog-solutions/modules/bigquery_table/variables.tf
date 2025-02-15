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

variable "project_id" {
  type        = string
  description = "Optional Project ID."
  default     = null
}

variable "dataset_id" {
  description = "The ID of the BigQuery dataset where the table will be created."
  type        = string
}

variable "table_id" {
  description = "The ID of the BigQuery table to create."
  type        = string
}

variable "schema" {
  description = "The schema for the BigQuery table in JSON format."
  type        = string
}

variable "deletion_protection" {
  description = "Whether or not to allow deletion of tables and external tables defined by this module. Can be overriden by table-level deletion_protection configuration."
  type        = bool
  default     = false
}

variable "expiration_time" {
  description = "The expiration time for the table in RFC 3339 format."
  type        = string
  default     = null
}

variable "region" {
  type        = string
  description = "The resource region, one of [us-central1, us-east4]."
  default     = "us-central1"
  validation {
    condition     = contains(["us-central1", "us-east4"], var.region)
    error_message = "Region must be one of [us-central1, us-east4]."
  }
}

variable "labels" {
  description = "Key value pairs in a map for dataset labels"
  type        = map(string)
  default     = {}
}

variable "keyring_name" {
  type        = string
  description = "Name of the keyring"
  default     = "sample-keyring"
}

variable "data_domain" {
  description = "Data Domain name."
  type        = string
  default     = "domain-1"
}
