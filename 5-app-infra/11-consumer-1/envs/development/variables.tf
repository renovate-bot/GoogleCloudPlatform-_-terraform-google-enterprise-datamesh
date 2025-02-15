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

variable "env" {
  description = "Environment"
  type        = string
}

variable "region" {
  description = "Region"
  type        = string
}

variable "dataset_id_prefix" {
  description = "Dataset ID prefix"
  type        = string
}

variable "remote_state_bucket" {
  description = "Name of the remote state bucket"
  type        = string
}

variable "consumer_name" {
  description = "Consumer name"
  type        = string
}

variable "business_unit" {
  description = "Business unit"
  type        = string
}

variable "business_code" {
  description = "Business code"
  type        = string
}
