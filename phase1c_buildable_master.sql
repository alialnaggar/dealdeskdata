-- Rendered from the Phase 1C structural and synthetic cost drafts.

-- Disposable fixture: never a production catalogue.

\set ON_ERROR_STOP on
BEGIN;
SET search_path TO deal_desk, public;

INSERT INTO products (product_id, product_code, catalog_version, product_name, category, product_type, attributes_json, list_price, standard_cost, billing_model, unit_of_measure, is_sellable, fulfillment_mode, stock_uom) VALUES
 ('SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-009', 'SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-009', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-009', 'end_user_computing_and_digital_workplace', 'physical', '{"archetype_code":"WORKSTATION","build_platform":"workstation","category":"end_user_computing_and_digital_workplace","demand_class":"regular","offered_options":["standard","alternate"],"subcategory":"workstation"}', '1050', '715', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-010', 'SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-010', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-010', 'end_user_computing_and_digital_workplace', 'physical', '{"archetype_code":"WORKSTATION","build_platform":"workstation","category":"end_user_computing_and_digital_workplace","demand_class":"regular","offered_options":["standard","alternate"],"subcategory":"workstation"}', '850', '692', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-001', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-001', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-001', 'servers_and_compute_infrastructure', 'physical', '{"archetype_code":"RACK_SERVER","build_platform":"server","category":"servers_and_compute_infrastructure","demand_class":"regular","offered_options":["standard","alternate"],"subcategory":"rack_server"}', '9740', '8178', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-002', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-002', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-002', 'servers_and_compute_infrastructure', 'physical', '{"archetype_code":"RACK_SERVER","build_platform":"server","category":"servers_and_compute_infrastructure","demand_class":"regular","offered_options":["standard","alternate"],"subcategory":"rack_server"}', '9770', '8201', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-003', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-003', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-003', 'servers_and_compute_infrastructure', 'physical', '{"archetype_code":"RACK_SERVER","build_platform":"server","category":"servers_and_compute_infrastructure","demand_class":"regular","offered_options":["standard","alternate"],"subcategory":"rack_server"}', '9770', '8205', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-004', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-004', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-004', 'servers_and_compute_infrastructure', 'physical', '{"archetype_code":"RACK_SERVER","build_platform":"server","category":"servers_and_compute_infrastructure","demand_class":"regular","offered_options":["standard","alternate"],"subcategory":"rack_server"}', '9750', '8183', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-005', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-005', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-005', 'servers_and_compute_infrastructure', 'physical', '{"archetype_code":"TOWER_SERVER","build_platform":"server","category":"servers_and_compute_infrastructure","demand_class":"regular","offered_options":["standard"],"subcategory":"tower_server"}', '9800', '8226', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-006', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-006', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-006', 'servers_and_compute_infrastructure', 'physical', '{"archetype_code":"TOWER_SERVER","build_platform":"server","category":"servers_and_compute_infrastructure","demand_class":"regular","offered_options":["standard"],"subcategory":"tower_server"}', '9710', '8150', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-007', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-007', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-007', 'servers_and_compute_infrastructure', 'physical', '{"archetype_code":"TOWER_SERVER","build_platform":"server","category":"servers_and_compute_infrastructure","demand_class":"regular","offered_options":["standard"],"subcategory":"tower_server"}', '9770', '8205', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-008', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-008', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-008', 'servers_and_compute_infrastructure', 'physical', '{"archetype_code":"EDGE_COMPACT_SERVER","build_platform":"server","category":"servers_and_compute_infrastructure","demand_class":"regular","offered_options":["standard"],"subcategory":"edge_compact_server"}', '9760', '8192', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-009', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-009', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-009', 'servers_and_compute_infrastructure', 'physical', '{"archetype_code":"EDGE_COMPACT_SERVER","build_platform":"server","category":"servers_and_compute_infrastructure","demand_class":"regular","offered_options":["standard"],"subcategory":"edge_compact_server"}', '9750', '8183', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-010', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-010', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-010', 'servers_and_compute_infrastructure', 'physical', '{"archetype_code":"GPU_ACCELERATED_SERVER","build_platform":"server","category":"servers_and_compute_infrastructure","demand_class":"regular","offered_options":["standard"],"subcategory":"gpu_accelerated_server"}', '9730', '8171', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('SELL-STORAGE_AND_DATA_PROTECTION-001', 'SELL-STORAGE_AND_DATA_PROTECTION-001', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-STORAGE_AND_DATA_PROTECTION-001', 'storage_and_data_protection', 'physical', '{"archetype_code":"STORAGE_ARRAY","build_platform":"storage_system","category":"storage_and_data_protection","demand_class":"regular","offered_options":["standard"],"subcategory":"storage_array"}', '8280', '6706', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('SELL-STORAGE_AND_DATA_PROTECTION-002', 'SELL-STORAGE_AND_DATA_PROTECTION-002', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-STORAGE_AND_DATA_PROTECTION-002', 'storage_and_data_protection', 'physical', '{"archetype_code":"STORAGE_ARRAY","build_platform":"storage_system","category":"storage_and_data_protection","demand_class":"regular","offered_options":["standard"],"subcategory":"storage_array"}', '8320', '6739', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('SELL-STORAGE_AND_DATA_PROTECTION-003', 'SELL-STORAGE_AND_DATA_PROTECTION-003', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-STORAGE_AND_DATA_PROTECTION-003', 'storage_and_data_protection', 'physical', '{"archetype_code":"STORAGE_ARRAY","build_platform":"storage_system","category":"storage_and_data_protection","demand_class":"regular","offered_options":["standard"],"subcategory":"storage_array"}', '8350', '6761', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('SELL-STORAGE_AND_DATA_PROTECTION-004', 'SELL-STORAGE_AND_DATA_PROTECTION-004', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-STORAGE_AND_DATA_PROTECTION-004', 'storage_and_data_protection', 'physical', '{"archetype_code":"NAS_FILE_STORAGE","build_platform":"storage_system","category":"storage_and_data_protection","demand_class":"regular","offered_options":["standard"],"subcategory":"nas_file_storage"}', '8280', '6706', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('SELL-STORAGE_AND_DATA_PROTECTION-005', 'SELL-STORAGE_AND_DATA_PROTECTION-005', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-STORAGE_AND_DATA_PROTECTION-005', 'storage_and_data_protection', 'physical', '{"archetype_code":"NAS_FILE_STORAGE","build_platform":"storage_system","category":"storage_and_data_protection","demand_class":"regular","offered_options":["standard"],"subcategory":"nas_file_storage"}', '8280', '6706', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('SELL-STORAGE_AND_DATA_PROTECTION-006', 'SELL-STORAGE_AND_DATA_PROTECTION-006', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-STORAGE_AND_DATA_PROTECTION-006', 'storage_and_data_protection', 'physical', '{"archetype_code":"BACKUP_APPLIANCE","build_platform":"storage_system","category":"storage_and_data_protection","demand_class":"regular","offered_options":["standard"],"subcategory":"backup_appliance"}', '8280', '6706', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('COMP-COMPUTE-001', 'COMP-COMPUTE-001', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-COMPUTE-001', 'components', 'component', '{"archetype_code":"COMP-COMPUTE","component_family":"compute","component_role":"compute_kit","demand_class":"regular","supported_platforms":["workstation"]}', '0', '240', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-COMPUTE-002', 'COMP-COMPUTE-002', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-COMPUTE-002', 'components', 'component', '{"archetype_code":"COMP-COMPUTE","component_family":"compute","component_role":"compute_kit","demand_class":"regular","supported_platforms":["workstation"]}', '0', '260', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-COMPUTE-003', 'COMP-COMPUTE-003', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-COMPUTE-003', 'components', 'component', '{"archetype_code":"COMP-COMPUTE","component_family":"compute","component_role":"compute_kit","demand_class":"regular","supported_platforms":["workstation"]}', '0', '242.40', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-COMPUTE-004', 'COMP-COMPUTE-004', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-COMPUTE-004', 'components', 'component', '{"archetype_code":"COMP-COMPUTE","component_family":"compute","component_role":"compute_kit","demand_class":"regular","supported_platforms":["server"]}', '0', '3800.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-COMPUTE-005', 'COMP-COMPUTE-005', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-COMPUTE-005', 'components', 'component', '{"archetype_code":"COMP-COMPUTE","component_family":"compute","component_role":"compute_kit","demand_class":"regular","supported_platforms":["server"]}', '0', '3819.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-COMPUTE-006', 'COMP-COMPUTE-006', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-COMPUTE-006', 'components', 'component', '{"archetype_code":"COMP-COMPUTE","component_family":"compute","component_role":"compute_kit","demand_class":"regular","supported_platforms":["server"]}', '0', '3838.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-COMPUTE-007', 'COMP-COMPUTE-007', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-COMPUTE-007', 'components', 'component', '{"archetype_code":"COMP-COMPUTE","component_family":"compute","component_role":"compute_kit","demand_class":"regular","supported_platforms":["server"]}', '0', '3800.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-COMPUTE-008', 'COMP-COMPUTE-008', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-COMPUTE-008', 'components', 'component', '{"archetype_code":"COMP-COMPUTE","component_family":"compute","component_role":"compute_kit","demand_class":"regular","supported_platforms":["server"]}', '0', '3819.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-COMPUTE-009', 'COMP-COMPUTE-009', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-COMPUTE-009', 'components', 'component', '{"archetype_code":"COMP-COMPUTE","component_family":"compute","component_role":"compute_kit","demand_class":"regular","supported_platforms":["server"]}', '0', '3838.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-COMPUTE-010', 'COMP-COMPUTE-010', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-COMPUTE-010', 'components', 'component', '{"archetype_code":"COMP-COMPUTE","component_family":"compute","component_role":"compute_kit","demand_class":"regular","supported_platforms":["storage_system"]}', '0', '1800.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-COMPUTE-011', 'COMP-COMPUTE-011', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-COMPUTE-011', 'components', 'component', '{"archetype_code":"COMP-COMPUTE","component_family":"compute","component_role":"compute_kit","demand_class":"regular","supported_platforms":["storage_system"]}', '0', '1809.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-COMPUTE-012', 'COMP-COMPUTE-012', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-COMPUTE-012', 'components', 'component', '{"archetype_code":"COMP-COMPUTE","component_family":"compute","component_role":"compute_kit","demand_class":"regular","supported_platforms":["storage_system"]}', '0', '1818.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-STORAGE-001', 'COMP-STORAGE-001', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-STORAGE-001', 'components', 'component', '{"archetype_code":"COMP-STORAGE","component_family":"storage","component_role":"storage_drive","demand_class":"regular","supported_platforms":["workstation"]}', '0', '60', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-STORAGE-002', 'COMP-STORAGE-002', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-STORAGE-002', 'components', 'component', '{"archetype_code":"COMP-STORAGE","component_family":"storage","component_role":"storage_drive","demand_class":"regular","supported_platforms":["workstation"]}', '0', '60', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-STORAGE-003', 'COMP-STORAGE-003', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-STORAGE-003', 'components', 'component', '{"archetype_code":"COMP-STORAGE","component_family":"storage","component_role":"storage_drive","demand_class":"regular","supported_platforms":["server"]}', '0', '909.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-STORAGE-004', 'COMP-STORAGE-004', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-STORAGE-004', 'components', 'component', '{"archetype_code":"COMP-STORAGE","component_family":"storage","component_role":"storage_drive","demand_class":"regular","supported_platforms":["server"]}', '0', '900.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-STORAGE-005', 'COMP-STORAGE-005', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-STORAGE-005', 'components', 'component', '{"archetype_code":"COMP-STORAGE","component_family":"storage","component_role":"storage_drive","demand_class":"regular","supported_platforms":["server"]}', '0', '904.50', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-STORAGE-006', 'COMP-STORAGE-006', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-STORAGE-006', 'components', 'component', '{"archetype_code":"COMP-STORAGE","component_family":"storage","component_role":"storage_drive","demand_class":"regular","supported_platforms":["server"]}', '0', '909.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-STORAGE-007', 'COMP-STORAGE-007', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-STORAGE-007', 'components', 'component', '{"archetype_code":"COMP-STORAGE","component_family":"storage","component_role":"storage_drive","demand_class":"regular","supported_platforms":["storage_system"]}', '0', '1300.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-STORAGE-008', 'COMP-STORAGE-008', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-STORAGE-008', 'components', 'component', '{"archetype_code":"COMP-STORAGE","component_family":"storage","component_role":"storage_drive","demand_class":"regular","supported_platforms":["storage_system"]}', '0', '1306.50', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-STORAGE-009', 'COMP-STORAGE-009', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-STORAGE-009', 'components', 'component', '{"archetype_code":"COMP-STORAGE","component_family":"storage","component_role":"storage_drive","demand_class":"regular","supported_platforms":["storage_system"]}', '0', '1313.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-NETWORK_AND_POWER-001', 'COMP-NETWORK_AND_POWER-001', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-NETWORK_AND_POWER-001', 'components', 'component', '{"archetype_code":"COMP-NETWORK_AND_POWER","component_family":"network_and_power","component_role":"network_power_kit","demand_class":"regular","supported_platforms":["workstation"]}', '0', '50', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-NETWORK_AND_POWER-002', 'COMP-NETWORK_AND_POWER-002', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-NETWORK_AND_POWER-002', 'components', 'component', '{"archetype_code":"COMP-NETWORK_AND_POWER","component_family":"network_and_power","component_role":"network_power_kit","demand_class":"regular","supported_platforms":["workstation"]}', '0', '50', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-NETWORK_AND_POWER-003', 'COMP-NETWORK_AND_POWER-003', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-NETWORK_AND_POWER-003', 'components', 'component', '{"archetype_code":"COMP-NETWORK_AND_POWER","component_family":"network_and_power","component_role":"network_power_kit","demand_class":"regular","supported_platforms":["server"]}', '0', '707.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-NETWORK_AND_POWER-004', 'COMP-NETWORK_AND_POWER-004', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-NETWORK_AND_POWER-004', 'components', 'component', '{"archetype_code":"COMP-NETWORK_AND_POWER","component_family":"network_and_power","component_role":"network_power_kit","demand_class":"regular","supported_platforms":["server"]}', '0', '700.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-NETWORK_AND_POWER-005', 'COMP-NETWORK_AND_POWER-005', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-NETWORK_AND_POWER-005', 'components', 'component', '{"archetype_code":"COMP-NETWORK_AND_POWER","component_family":"network_and_power","component_role":"network_power_kit","demand_class":"regular","supported_platforms":["server"]}', '0', '703.50', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-NETWORK_AND_POWER-006', 'COMP-NETWORK_AND_POWER-006', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-NETWORK_AND_POWER-006', 'components', 'component', '{"archetype_code":"COMP-NETWORK_AND_POWER","component_family":"network_and_power","component_role":"network_power_kit","demand_class":"regular","supported_platforms":["server"]}', '0', '707.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-NETWORK_AND_POWER-007', 'COMP-NETWORK_AND_POWER-007', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-NETWORK_AND_POWER-007', 'components', 'component', '{"archetype_code":"COMP-NETWORK_AND_POWER","component_family":"network_and_power","component_role":"network_power_kit","demand_class":"regular","supported_platforms":["storage_system"]}', '0', '600.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-NETWORK_AND_POWER-008', 'COMP-NETWORK_AND_POWER-008', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-NETWORK_AND_POWER-008', 'components', 'component', '{"archetype_code":"COMP-NETWORK_AND_POWER","component_family":"network_and_power","component_role":"network_power_kit","demand_class":"regular","supported_platforms":["storage_system"]}', '0', '603.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-NETWORK_AND_POWER-009', 'COMP-NETWORK_AND_POWER-009', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-NETWORK_AND_POWER-009', 'components', 'component', '{"archetype_code":"COMP-NETWORK_AND_POWER","component_family":"network_and_power","component_role":"network_power_kit","demand_class":"regular","supported_platforms":["storage_system"]}', '0', '606.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-CHASSIS_AND_OTHER-001', 'COMP-CHASSIS_AND_OTHER-001', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-CHASSIS_AND_OTHER-001', 'components', 'component', '{"archetype_code":"COMP-CHASSIS_AND_OTHER","component_family":"chassis_and_other","component_role":"enclosure_kit","demand_class":"regular","supported_platforms":["workstation"]}', '0', '180.0', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-CHASSIS_AND_OTHER-002', 'COMP-CHASSIS_AND_OTHER-002', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-CHASSIS_AND_OTHER-002', 'components', 'component', '{"archetype_code":"COMP-CHASSIS_AND_OTHER","component_family":"chassis_and_other","component_role":"enclosure_kit","demand_class":"regular","supported_platforms":["server"]}', '0', '1005.0', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-CHASSIS_AND_OTHER-003', 'COMP-CHASSIS_AND_OTHER-003', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-CHASSIS_AND_OTHER-003', 'components', 'component', '{"archetype_code":"COMP-CHASSIS_AND_OTHER","component_family":"chassis_and_other","component_role":"enclosure_kit","demand_class":"regular","supported_platforms":["server"]}', '0', '1010.0', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-CHASSIS_AND_OTHER-004', 'COMP-CHASSIS_AND_OTHER-004', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-CHASSIS_AND_OTHER-004', 'components', 'component', '{"archetype_code":"COMP-CHASSIS_AND_OTHER","component_family":"chassis_and_other","component_role":"enclosure_kit","demand_class":"regular","supported_platforms":["server"]}', '0', '1000.0', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-CHASSIS_AND_OTHER-005', 'COMP-CHASSIS_AND_OTHER-005', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-CHASSIS_AND_OTHER-005', 'components', 'component', '{"archetype_code":"COMP-CHASSIS_AND_OTHER","component_family":"chassis_and_other","component_role":"enclosure_kit","demand_class":"regular","supported_platforms":["storage_system"]}', '0', '1005.0', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-CHASSIS_AND_OTHER-006', 'COMP-CHASSIS_AND_OTHER-006', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-CHASSIS_AND_OTHER-006', 'components', 'component', '{"archetype_code":"COMP-CHASSIS_AND_OTHER","component_family":"chassis_and_other","component_role":"enclosure_kit","demand_class":"regular","supported_platforms":["storage_system"]}', '0', '1010.0', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit');

INSERT INTO bom_headers (bom_id, finished_product_id, catalog_version, bom_version, configuration_signature_json, output_quantity, effective_from, effective_to, status) VALUES
 ('BOM-001', 'SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-009', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-002', 'SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-009', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["alternate"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-003', 'SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-010', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-004', 'SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-010', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["alternate"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-005', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-001', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-006', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-001', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["alternate"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-007', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-002', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-008', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-002', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["alternate"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-009', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-003', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-010', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-003', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["alternate"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-011', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-004', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-012', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-004', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["alternate"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-013', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-005', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-014', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-006', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-015', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-007', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-016', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-008', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-017', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-009', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-018', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-010', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-019', 'SELL-STORAGE_AND_DATA_PROTECTION-001', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-020', 'SELL-STORAGE_AND_DATA_PROTECTION-002', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-021', 'SELL-STORAGE_AND_DATA_PROTECTION-003', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-022', 'SELL-STORAGE_AND_DATA_PROTECTION-004', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-023', 'SELL-STORAGE_AND_DATA_PROTECTION-005', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-024', 'SELL-STORAGE_AND_DATA_PROTECTION-006', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active');

INSERT INTO bom_lines (bom_line_id, bom_id, component_product_id, required_quantity_per_output, scrap_pct, substitute_group_code, priority, is_mandatory) VALUES
 ('BOM-001-1', 'BOM-001', 'COMP-COMPUTE-001', '1', '0', NULL, '0', TRUE),
 ('BOM-001-2', 'BOM-001', 'COMP-STORAGE-001', '2', '1', NULL, '0', TRUE),
 ('BOM-001-3', 'BOM-001', 'COMP-NETWORK_AND_POWER-001', '1', '0', 'NETWORK_OPTION', '0', TRUE),
 ('BOM-001-4', 'BOM-001', 'COMP-CHASSIS_AND_OTHER-001', '1', '0', NULL, '0', TRUE),
 ('BOM-001-NETWORK-ALT', 'BOM-001', 'COMP-NETWORK_AND_POWER-002', '1', '0', 'NETWORK_OPTION', '1', TRUE),
 ('BOM-002-1', 'BOM-002', 'COMP-COMPUTE-002', '1', '0', NULL, '0', TRUE),
 ('BOM-002-2', 'BOM-002', 'COMP-STORAGE-002', '2', '1', NULL, '0', TRUE),
 ('BOM-002-3', 'BOM-002', 'COMP-NETWORK_AND_POWER-002', '1', '0', NULL, '0', TRUE),
 ('BOM-002-4', 'BOM-002', 'COMP-CHASSIS_AND_OTHER-001', '1', '0', NULL, '0', TRUE),
 ('BOM-003-1', 'BOM-003', 'COMP-COMPUTE-003', '1', '0', NULL, '0', TRUE),
 ('BOM-003-2', 'BOM-003', 'COMP-STORAGE-001', '2', '1', NULL, '0', TRUE),
 ('BOM-003-3', 'BOM-003', 'COMP-NETWORK_AND_POWER-001', '1', '0', NULL, '0', TRUE),
 ('BOM-003-4', 'BOM-003', 'COMP-CHASSIS_AND_OTHER-001', '1', '0', NULL, '0', TRUE),
 ('BOM-004-1', 'BOM-004', 'COMP-COMPUTE-001', '1', '0', NULL, '0', TRUE),
 ('BOM-004-2', 'BOM-004', 'COMP-STORAGE-001', '2', '1', NULL, '0', TRUE),
 ('BOM-004-3', 'BOM-004', 'COMP-NETWORK_AND_POWER-001', '1', '0', NULL, '0', TRUE),
 ('BOM-004-4', 'BOM-004', 'COMP-CHASSIS_AND_OTHER-001', '1', '0', NULL, '0', TRUE),
 ('BOM-005-1', 'BOM-005', 'COMP-COMPUTE-004', '1', '0', NULL, '0', TRUE),
 ('BOM-005-2', 'BOM-005', 'COMP-STORAGE-003', '2', '1', NULL, '0', TRUE),
 ('BOM-005-3', 'BOM-005', 'COMP-NETWORK_AND_POWER-003', '1', '0', NULL, '0', TRUE),
 ('BOM-005-4', 'BOM-005', 'COMP-CHASSIS_AND_OTHER-002', '1', '0', NULL, '0', TRUE),
 ('BOM-006-1', 'BOM-006', 'COMP-COMPUTE-005', '1', '0', NULL, '0', TRUE),
 ('BOM-006-2', 'BOM-006', 'COMP-STORAGE-004', '2', '1', NULL, '0', TRUE),
 ('BOM-006-3', 'BOM-006', 'COMP-NETWORK_AND_POWER-004', '1', '0', NULL, '0', TRUE),
 ('BOM-006-4', 'BOM-006', 'COMP-CHASSIS_AND_OTHER-003', '1', '0', NULL, '0', TRUE),
 ('BOM-007-1', 'BOM-007', 'COMP-COMPUTE-006', '1', '0', NULL, '0', TRUE),
 ('BOM-007-2', 'BOM-007', 'COMP-STORAGE-005', '2', '1', NULL, '0', TRUE),
 ('BOM-007-3', 'BOM-007', 'COMP-NETWORK_AND_POWER-005', '1', '0', NULL, '0', TRUE),
 ('BOM-007-4', 'BOM-007', 'COMP-CHASSIS_AND_OTHER-004', '1', '0', NULL, '0', TRUE),
 ('BOM-008-1', 'BOM-008', 'COMP-COMPUTE-007', '1', '0', NULL, '0', TRUE),
 ('BOM-008-2', 'BOM-008', 'COMP-STORAGE-006', '2', '1', NULL, '0', TRUE),
 ('BOM-008-3', 'BOM-008', 'COMP-NETWORK_AND_POWER-006', '1', '0', NULL, '0', TRUE),
 ('BOM-008-4', 'BOM-008', 'COMP-CHASSIS_AND_OTHER-002', '1', '0', NULL, '0', TRUE),
 ('BOM-009-1', 'BOM-009', 'COMP-COMPUTE-008', '1', '0', NULL, '0', TRUE),
 ('BOM-009-2', 'BOM-009', 'COMP-STORAGE-003', '2', '1', NULL, '0', TRUE),
 ('BOM-009-3', 'BOM-009', 'COMP-NETWORK_AND_POWER-003', '1', '0', NULL, '0', TRUE),
 ('BOM-009-4', 'BOM-009', 'COMP-CHASSIS_AND_OTHER-003', '1', '0', NULL, '0', TRUE),
 ('BOM-010-1', 'BOM-010', 'COMP-COMPUTE-009', '1', '0', NULL, '0', TRUE),
 ('BOM-010-2', 'BOM-010', 'COMP-STORAGE-004', '2', '1', NULL, '0', TRUE),
 ('BOM-010-3', 'BOM-010', 'COMP-NETWORK_AND_POWER-004', '1', '0', NULL, '0', TRUE),
 ('BOM-010-4', 'BOM-010', 'COMP-CHASSIS_AND_OTHER-002', '1', '0', NULL, '0', TRUE),
 ('BOM-011-1', 'BOM-011', 'COMP-COMPUTE-004', '1', '0', NULL, '0', TRUE),
 ('BOM-011-2', 'BOM-011', 'COMP-STORAGE-003', '2', '1', NULL, '0', TRUE),
 ('BOM-011-3', 'BOM-011', 'COMP-NETWORK_AND_POWER-003', '1', '0', NULL, '0', TRUE),
 ('BOM-011-4', 'BOM-011', 'COMP-CHASSIS_AND_OTHER-003', '1', '0', NULL, '0', TRUE),
 ('BOM-012-1', 'BOM-012', 'COMP-COMPUTE-005', '1', '0', NULL, '0', TRUE),
 ('BOM-012-2', 'BOM-012', 'COMP-STORAGE-004', '2', '1', NULL, '0', TRUE),
 ('BOM-012-3', 'BOM-012', 'COMP-NETWORK_AND_POWER-004', '1', '0', NULL, '0', TRUE),
 ('BOM-012-4', 'BOM-012', 'COMP-CHASSIS_AND_OTHER-002', '1', '0', NULL, '0', TRUE),
 ('BOM-013-1', 'BOM-013', 'COMP-COMPUTE-006', '1', '0', NULL, '0', TRUE),
 ('BOM-013-2', 'BOM-013', 'COMP-STORAGE-003', '2', '1', NULL, '0', TRUE),
 ('BOM-013-3', 'BOM-013', 'COMP-NETWORK_AND_POWER-003', '1', '0', NULL, '0', TRUE),
 ('BOM-013-4', 'BOM-013', 'COMP-CHASSIS_AND_OTHER-003', '1', '0', NULL, '0', TRUE),
 ('BOM-014-1', 'BOM-014', 'COMP-COMPUTE-004', '1', '0', NULL, '0', TRUE),
 ('BOM-014-2', 'BOM-014', 'COMP-STORAGE-004', '2', '1', NULL, '0', TRUE),
 ('BOM-014-3', 'BOM-014', 'COMP-NETWORK_AND_POWER-004', '1', '0', NULL, '0', TRUE),
 ('BOM-014-4', 'BOM-014', 'COMP-CHASSIS_AND_OTHER-002', '1', '0', NULL, '0', TRUE),
 ('BOM-015-1', 'BOM-015', 'COMP-COMPUTE-005', '1', '0', NULL, '0', TRUE),
 ('BOM-015-2', 'BOM-015', 'COMP-STORAGE-003', '2', '1', NULL, '0', TRUE),
 ('BOM-015-3', 'BOM-015', 'COMP-NETWORK_AND_POWER-003', '1', '0', NULL, '0', TRUE),
 ('BOM-015-4', 'BOM-015', 'COMP-CHASSIS_AND_OTHER-003', '1', '0', NULL, '0', TRUE),
 ('BOM-016-1', 'BOM-016', 'COMP-COMPUTE-006', '1', '0', NULL, '0', TRUE),
 ('BOM-016-2', 'BOM-016', 'COMP-STORAGE-004', '2', '1', NULL, '0', TRUE),
 ('BOM-016-3', 'BOM-016', 'COMP-NETWORK_AND_POWER-004', '1', '0', NULL, '0', TRUE),
 ('BOM-016-4', 'BOM-016', 'COMP-CHASSIS_AND_OTHER-002', '1', '0', NULL, '0', TRUE),
 ('BOM-017-1', 'BOM-017', 'COMP-COMPUTE-004', '1', '0', NULL, '0', TRUE),
 ('BOM-017-2', 'BOM-017', 'COMP-STORAGE-003', '2', '1', NULL, '0', TRUE),
 ('BOM-017-3', 'BOM-017', 'COMP-NETWORK_AND_POWER-003', '1', '0', NULL, '0', TRUE),
 ('BOM-017-4', 'BOM-017', 'COMP-CHASSIS_AND_OTHER-003', '1', '0', NULL, '0', TRUE),
 ('BOM-018-1', 'BOM-018', 'COMP-COMPUTE-005', '1', '0', NULL, '0', TRUE),
 ('BOM-018-2', 'BOM-018', 'COMP-STORAGE-004', '2', '1', NULL, '0', TRUE),
 ('BOM-018-3', 'BOM-018', 'COMP-NETWORK_AND_POWER-004', '1', '0', NULL, '0', TRUE),
 ('BOM-018-4', 'BOM-018', 'COMP-CHASSIS_AND_OTHER-002', '1', '0', NULL, '0', TRUE),
 ('BOM-019-1', 'BOM-019', 'COMP-COMPUTE-010', '1', '0', NULL, '0', TRUE),
 ('BOM-019-2', 'BOM-019', 'COMP-STORAGE-007', '2', '1', NULL, '0', TRUE),
 ('BOM-019-3', 'BOM-019', 'COMP-NETWORK_AND_POWER-007', '1', '0', NULL, '0', TRUE),
 ('BOM-019-4', 'BOM-019', 'COMP-CHASSIS_AND_OTHER-005', '1', '0', NULL, '0', TRUE),
 ('BOM-020-1', 'BOM-020', 'COMP-COMPUTE-011', '1', '0', NULL, '0', TRUE),
 ('BOM-020-2', 'BOM-020', 'COMP-STORAGE-008', '2', '1', NULL, '0', TRUE),
 ('BOM-020-3', 'BOM-020', 'COMP-NETWORK_AND_POWER-008', '1', '0', NULL, '0', TRUE),
 ('BOM-020-4', 'BOM-020', 'COMP-CHASSIS_AND_OTHER-006', '1', '0', NULL, '0', TRUE),
 ('BOM-021-1', 'BOM-021', 'COMP-COMPUTE-012', '1', '0', NULL, '0', TRUE),
 ('BOM-021-2', 'BOM-021', 'COMP-STORAGE-009', '2', '1', NULL, '0', TRUE),
 ('BOM-021-3', 'BOM-021', 'COMP-NETWORK_AND_POWER-009', '1', '0', NULL, '0', TRUE),
 ('BOM-021-4', 'BOM-021', 'COMP-CHASSIS_AND_OTHER-005', '1', '0', NULL, '0', TRUE),
 ('BOM-022-1', 'BOM-022', 'COMP-COMPUTE-010', '1', '0', NULL, '0', TRUE),
 ('BOM-022-2', 'BOM-022', 'COMP-STORAGE-007', '2', '1', NULL, '0', TRUE),
 ('BOM-022-3', 'BOM-022', 'COMP-NETWORK_AND_POWER-007', '1', '0', NULL, '0', TRUE),
 ('BOM-022-4', 'BOM-022', 'COMP-CHASSIS_AND_OTHER-005', '1', '0', NULL, '0', TRUE),
 ('BOM-023-1', 'BOM-023', 'COMP-COMPUTE-010', '1', '0', NULL, '0', TRUE),
 ('BOM-023-2', 'BOM-023', 'COMP-STORAGE-007', '2', '1', NULL, '0', TRUE),
 ('BOM-023-3', 'BOM-023', 'COMP-NETWORK_AND_POWER-007', '1', '0', NULL, '0', TRUE),
 ('BOM-023-4', 'BOM-023', 'COMP-CHASSIS_AND_OTHER-005', '1', '0', NULL, '0', TRUE),
 ('BOM-024-1', 'BOM-024', 'COMP-COMPUTE-010', '1', '0', NULL, '0', TRUE),
 ('BOM-024-2', 'BOM-024', 'COMP-STORAGE-007', '2', '1', NULL, '0', TRUE),
 ('BOM-024-3', 'BOM-024', 'COMP-NETWORK_AND_POWER-007', '1', '0', NULL, '0', TRUE),
 ('BOM-024-4', 'BOM-024', 'COMP-CHASSIS_AND_OTHER-005', '1', '0', NULL, '0', TRUE);

INSERT INTO production_requirements (requirement_id, bom_id, operation_seq, capability_code, resource_type, setup_hours, hours_per_unit, batch_size, status) VALUES
 ('BOM-001-1', 'BOM-001', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-001-2', 'BOM-001', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-002-1', 'BOM-002', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-002-2', 'BOM-002', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-003-1', 'BOM-003', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-003-2', 'BOM-003', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-004-1', 'BOM-004', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-004-2', 'BOM-004', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-005-1', 'BOM-005', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-005-2', 'BOM-005', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-006-1', 'BOM-006', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-006-2', 'BOM-006', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-007-1', 'BOM-007', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-007-2', 'BOM-007', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-008-1', 'BOM-008', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-008-2', 'BOM-008', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-009-1', 'BOM-009', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-009-2', 'BOM-009', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-010-1', 'BOM-010', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-010-2', 'BOM-010', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-011-1', 'BOM-011', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-011-2', 'BOM-011', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-012-1', 'BOM-012', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-012-2', 'BOM-012', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-013-1', 'BOM-013', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-013-2', 'BOM-013', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-014-1', 'BOM-014', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-014-2', 'BOM-014', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-015-1', 'BOM-015', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-015-2', 'BOM-015', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-016-1', 'BOM-016', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-016-2', 'BOM-016', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-017-1', 'BOM-017', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-017-2', 'BOM-017', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-018-1', 'BOM-018', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-018-2', 'BOM-018', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-019-1', 'BOM-019', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-019-2', 'BOM-019', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-020-1', 'BOM-020', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-020-2', 'BOM-020', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-021-1', 'BOM-021', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-021-2', 'BOM-021', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-022-1', 'BOM-022', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-022-2', 'BOM-022', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-023-1', 'BOM-023', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-023-2', 'BOM-023', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-024-1', 'BOM-024', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-024-2', 'BOM-024', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active');


DO $fixture$
DECLARE
    product_count INTEGER;
    bom_count INTEGER;
    component_count INTEGER;
    bad_count INTEGER;
BEGIN
    SELECT count(*) INTO product_count FROM products WHERE fulfillment_mode = 'make_to_order';
    SELECT count(*) INTO bom_count FROM bom_headers;
    SELECT count(*) INTO component_count FROM products WHERE fulfillment_mode = 'component';
    IF product_count <> 18 OR bom_count <> 24 OR component_count <> 36 THEN
        RAISE EXCEPTION 'buildable master fixture counts differ: %, %, %',
            product_count, bom_count, component_count;
    END IF;

    SELECT count(*) INTO bad_count
    FROM bom_lines l JOIN bom_headers h USING (bom_id)
      JOIN products part ON part.product_id = l.component_product_id
      JOIN products finished ON finished.product_id = h.finished_product_id
    WHERE NOT (part.attributes_json->'supported_platforms' ?
               (finished.attributes_json->>'build_platform'));
    IF bad_count <> 0 THEN
        RAISE EXCEPTION 'component platform mismatch in master slice';
    END IF;

    SELECT count(*) INTO bad_count FROM bom_lines
    WHERE bom_line_id IN ('BOM-001-1', 'BOM-001-2', 'BOM-001-3', 'BOM-001-4', 'BOM-002-1', 'BOM-002-2', 'BOM-002-3', 'BOM-002-4', 'BOM-003-1', 'BOM-003-2', 'BOM-003-3', 'BOM-003-4', 'BOM-004-1', 'BOM-004-2', 'BOM-004-3', 'BOM-004-4', 'BOM-005-1', 'BOM-005-2', 'BOM-005-3', 'BOM-005-4', 'BOM-006-1', 'BOM-006-2', 'BOM-006-3', 'BOM-006-4', 'BOM-007-1', 'BOM-007-2', 'BOM-007-3', 'BOM-007-4', 'BOM-008-1', 'BOM-008-2', 'BOM-008-3', 'BOM-008-4', 'BOM-009-1', 'BOM-009-2', 'BOM-009-3', 'BOM-009-4', 'BOM-010-1', 'BOM-010-2', 'BOM-010-3', 'BOM-010-4', 'BOM-011-1', 'BOM-011-2', 'BOM-011-3', 'BOM-011-4', 'BOM-012-1', 'BOM-012-2', 'BOM-012-3', 'BOM-012-4', 'BOM-013-1', 'BOM-013-2', 'BOM-013-3', 'BOM-013-4', 'BOM-014-1', 'BOM-014-2', 'BOM-014-3', 'BOM-014-4', 'BOM-015-1', 'BOM-015-2', 'BOM-015-3', 'BOM-015-4', 'BOM-016-1', 'BOM-016-2', 'BOM-016-3', 'BOM-016-4', 'BOM-017-1', 'BOM-017-2', 'BOM-017-3', 'BOM-017-4', 'BOM-018-1', 'BOM-018-2', 'BOM-018-3', 'BOM-018-4', 'BOM-019-1', 'BOM-019-2', 'BOM-019-3', 'BOM-019-4', 'BOM-020-1', 'BOM-020-2', 'BOM-020-3', 'BOM-020-4', 'BOM-021-1', 'BOM-021-2', 'BOM-021-3', 'BOM-021-4', 'BOM-022-1', 'BOM-022-2', 'BOM-022-3', 'BOM-022-4', 'BOM-023-1', 'BOM-023-2', 'BOM-023-3', 'BOM-023-4', 'BOM-024-1', 'BOM-024-2', 'BOM-024-3', 'BOM-024-4');
    IF bad_count <> 96 THEN
        RAISE EXCEPTION 'selected BOM lines missing from master fixture';
    END IF;

    WITH selected_material AS (
        SELECT h.bom_id, h.finished_product_id,
               sum(l.required_quantity_per_output / h.output_quantity /
                   (1 - l.scrap_pct / 100) * part.standard_cost) AS material
        FROM bom_headers h JOIN bom_lines l USING (bom_id)
          JOIN products part ON part.product_id = l.component_product_id
        WHERE l.bom_line_id IN ('BOM-001-1', 'BOM-001-2', 'BOM-001-3', 'BOM-001-4', 'BOM-002-1', 'BOM-002-2', 'BOM-002-3', 'BOM-002-4', 'BOM-003-1', 'BOM-003-2', 'BOM-003-3', 'BOM-003-4', 'BOM-004-1', 'BOM-004-2', 'BOM-004-3', 'BOM-004-4', 'BOM-005-1', 'BOM-005-2', 'BOM-005-3', 'BOM-005-4', 'BOM-006-1', 'BOM-006-2', 'BOM-006-3', 'BOM-006-4', 'BOM-007-1', 'BOM-007-2', 'BOM-007-3', 'BOM-007-4', 'BOM-008-1', 'BOM-008-2', 'BOM-008-3', 'BOM-008-4', 'BOM-009-1', 'BOM-009-2', 'BOM-009-3', 'BOM-009-4', 'BOM-010-1', 'BOM-010-2', 'BOM-010-3', 'BOM-010-4', 'BOM-011-1', 'BOM-011-2', 'BOM-011-3', 'BOM-011-4', 'BOM-012-1', 'BOM-012-2', 'BOM-012-3', 'BOM-012-4', 'BOM-013-1', 'BOM-013-2', 'BOM-013-3', 'BOM-013-4', 'BOM-014-1', 'BOM-014-2', 'BOM-014-3', 'BOM-014-4', 'BOM-015-1', 'BOM-015-2', 'BOM-015-3', 'BOM-015-4', 'BOM-016-1', 'BOM-016-2', 'BOM-016-3', 'BOM-016-4', 'BOM-017-1', 'BOM-017-2', 'BOM-017-3', 'BOM-017-4', 'BOM-018-1', 'BOM-018-2', 'BOM-018-3', 'BOM-018-4', 'BOM-019-1', 'BOM-019-2', 'BOM-019-3', 'BOM-019-4', 'BOM-020-1', 'BOM-020-2', 'BOM-020-3', 'BOM-020-4', 'BOM-021-1', 'BOM-021-2', 'BOM-021-3', 'BOM-021-4', 'BOM-022-1', 'BOM-022-2', 'BOM-022-3', 'BOM-022-4', 'BOM-023-1', 'BOM-023-2', 'BOM-023-3', 'BOM-023-4', 'BOM-024-1', 'BOM-024-2', 'BOM-024-3', 'BOM-024-4')
        GROUP BY h.bom_id, h.finished_product_id
    ), labor AS (
        SELECT bom_id, sum(setup_hours + hours_per_unit) * 30 AS labor_cost
        FROM production_requirements
        WHERE resource_type = 'workforce' AND status = 'active'
        GROUP BY bom_id
    ), rolled AS (
        SELECT m.bom_id, m.finished_product_id, finished.standard_cost,
               (m.material + labor.labor_cost) * 1.1 AS rollup
        FROM selected_material m JOIN labor USING (bom_id)
          JOIN products finished ON finished.product_id = m.finished_product_id
    )
    SELECT count(*) FILTER (WHERE abs(standard_cost - rollup) / rollup > 0.05)
           + count(*) FILTER (WHERE standard_cost < rollup)
           + CASE WHEN count(*) = 24 THEN 0 ELSE 1 END INTO bad_count FROM rolled;
    IF bad_count <> 0 THEN
        RAISE EXCEPTION 'BOM rollup or shared conservative cost failed in PostgreSQL';
    END IF;
END
$fixture$;
\if :{?phase1c_keep_transaction}
\else
ROLLBACK;
\endif
