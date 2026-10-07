-- Rendered from the Phase 1C structural and synthetic cost drafts.

-- Disposable fixture: never a production catalogue.

\set ON_ERROR_STOP on
BEGIN;
SET search_path TO deal_desk, public;

INSERT INTO products (product_id, product_code, catalog_version, product_name, category, product_type, attributes_json, list_price, standard_cost, billing_model, unit_of_measure, is_sellable, fulfillment_mode, stock_uom) VALUES
 ('SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-009', 'SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-009', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-009', 'end_user_computing_and_digital_workplace', 'physical', '{"archetype_code":"WORKSTATION","build_platform":"workstation","category":"end_user_computing_and_digital_workplace","demand_class":"regular","offered_options":["standard","alternate"],"subcategory":"workstation"}', '1050', '715', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-001', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-001', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-001', 'servers_and_compute_infrastructure', 'physical', '{"archetype_code":"RACK_SERVER","build_platform":"server","category":"servers_and_compute_infrastructure","demand_class":"regular","offered_options":["standard","alternate"],"subcategory":"rack_server"}', '9740', '8178', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('SELL-STORAGE_AND_DATA_PROTECTION-001', 'SELL-STORAGE_AND_DATA_PROTECTION-001', 'CATALOGUE_2026_V1', 'Synthetic fixture SELL-STORAGE_AND_DATA_PROTECTION-001', 'storage_and_data_protection', 'physical', '{"archetype_code":"STORAGE_ARRAY","build_platform":"storage_system","category":"storage_and_data_protection","demand_class":"regular","offered_options":["standard"],"subcategory":"storage_array"}', '8280', '6706', 'one_time', 'device', TRUE, 'make_to_order', 'each'),
 ('COMP-COMPUTE-001', 'COMP-COMPUTE-001', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-COMPUTE-001', 'components', 'component', '{"archetype_code":"COMP-COMPUTE","component_family":"compute","component_role":"compute_kit","demand_class":"regular","supported_platforms":["workstation"]}', '0', '240', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-COMPUTE-002', 'COMP-COMPUTE-002', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-COMPUTE-002', 'components', 'component', '{"archetype_code":"COMP-COMPUTE","component_family":"compute","component_role":"compute_kit","demand_class":"regular","supported_platforms":["workstation"]}', '0', '260', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-COMPUTE-004', 'COMP-COMPUTE-004', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-COMPUTE-004', 'components', 'component', '{"archetype_code":"COMP-COMPUTE","component_family":"compute","component_role":"compute_kit","demand_class":"regular","supported_platforms":["server"]}', '0', '3800.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-COMPUTE-005', 'COMP-COMPUTE-005', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-COMPUTE-005', 'components', 'component', '{"archetype_code":"COMP-COMPUTE","component_family":"compute","component_role":"compute_kit","demand_class":"regular","supported_platforms":["server"]}', '0', '3819.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-COMPUTE-010', 'COMP-COMPUTE-010', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-COMPUTE-010', 'components', 'component', '{"archetype_code":"COMP-COMPUTE","component_family":"compute","component_role":"compute_kit","demand_class":"regular","supported_platforms":["storage_system"]}', '0', '1800.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-STORAGE-001', 'COMP-STORAGE-001', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-STORAGE-001', 'components', 'component', '{"archetype_code":"COMP-STORAGE","component_family":"storage","component_role":"storage_drive","demand_class":"regular","supported_platforms":["workstation"]}', '0', '60', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-STORAGE-002', 'COMP-STORAGE-002', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-STORAGE-002', 'components', 'component', '{"archetype_code":"COMP-STORAGE","component_family":"storage","component_role":"storage_drive","demand_class":"regular","supported_platforms":["workstation"]}', '0', '60', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-STORAGE-003', 'COMP-STORAGE-003', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-STORAGE-003', 'components', 'component', '{"archetype_code":"COMP-STORAGE","component_family":"storage","component_role":"storage_drive","demand_class":"regular","supported_platforms":["server"]}', '0', '909.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-STORAGE-004', 'COMP-STORAGE-004', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-STORAGE-004', 'components', 'component', '{"archetype_code":"COMP-STORAGE","component_family":"storage","component_role":"storage_drive","demand_class":"regular","supported_platforms":["server"]}', '0', '900.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-STORAGE-007', 'COMP-STORAGE-007', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-STORAGE-007', 'components', 'component', '{"archetype_code":"COMP-STORAGE","component_family":"storage","component_role":"storage_drive","demand_class":"regular","supported_platforms":["storage_system"]}', '0', '1300.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-NETWORK_AND_POWER-001', 'COMP-NETWORK_AND_POWER-001', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-NETWORK_AND_POWER-001', 'components', 'component', '{"archetype_code":"COMP-NETWORK_AND_POWER","component_family":"network_and_power","component_role":"network_power_kit","demand_class":"regular","supported_platforms":["workstation"]}', '0', '50', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-NETWORK_AND_POWER-002', 'COMP-NETWORK_AND_POWER-002', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-NETWORK_AND_POWER-002', 'components', 'component', '{"archetype_code":"COMP-NETWORK_AND_POWER","component_family":"network_and_power","component_role":"network_power_kit","demand_class":"regular","supported_platforms":["workstation"]}', '0', '50', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-NETWORK_AND_POWER-003', 'COMP-NETWORK_AND_POWER-003', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-NETWORK_AND_POWER-003', 'components', 'component', '{"archetype_code":"COMP-NETWORK_AND_POWER","component_family":"network_and_power","component_role":"network_power_kit","demand_class":"regular","supported_platforms":["server"]}', '0', '707.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-NETWORK_AND_POWER-004', 'COMP-NETWORK_AND_POWER-004', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-NETWORK_AND_POWER-004', 'components', 'component', '{"archetype_code":"COMP-NETWORK_AND_POWER","component_family":"network_and_power","component_role":"network_power_kit","demand_class":"regular","supported_platforms":["server"]}', '0', '700.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-NETWORK_AND_POWER-007', 'COMP-NETWORK_AND_POWER-007', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-NETWORK_AND_POWER-007', 'components', 'component', '{"archetype_code":"COMP-NETWORK_AND_POWER","component_family":"network_and_power","component_role":"network_power_kit","demand_class":"regular","supported_platforms":["storage_system"]}', '0', '600.00', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-CHASSIS_AND_OTHER-001', 'COMP-CHASSIS_AND_OTHER-001', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-CHASSIS_AND_OTHER-001', 'components', 'component', '{"archetype_code":"COMP-CHASSIS_AND_OTHER","component_family":"chassis_and_other","component_role":"enclosure_kit","demand_class":"regular","supported_platforms":["workstation"]}', '0', '180.0', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-CHASSIS_AND_OTHER-002', 'COMP-CHASSIS_AND_OTHER-002', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-CHASSIS_AND_OTHER-002', 'components', 'component', '{"archetype_code":"COMP-CHASSIS_AND_OTHER","component_family":"chassis_and_other","component_role":"enclosure_kit","demand_class":"regular","supported_platforms":["server"]}', '0', '1005.0', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-CHASSIS_AND_OTHER-003', 'COMP-CHASSIS_AND_OTHER-003', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-CHASSIS_AND_OTHER-003', 'components', 'component', '{"archetype_code":"COMP-CHASSIS_AND_OTHER","component_family":"chassis_and_other","component_role":"enclosure_kit","demand_class":"regular","supported_platforms":["server"]}', '0', '1010.0', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit'),
 ('COMP-CHASSIS_AND_OTHER-005', 'COMP-CHASSIS_AND_OTHER-005', 'CATALOGUE_2026_V1', 'Synthetic fixture COMP-CHASSIS_AND_OTHER-005', 'components', 'component', '{"archetype_code":"COMP-CHASSIS_AND_OTHER","component_family":"chassis_and_other","component_role":"enclosure_kit","demand_class":"regular","supported_platforms":["storage_system"]}', '0', '1005.0', 'not_applicable', 'component_unit', FALSE, 'component', 'component_unit');

INSERT INTO bom_headers (bom_id, finished_product_id, catalog_version, bom_version, configuration_signature_json, output_quantity, effective_from, effective_to, status) VALUES
 ('BOM-001', 'SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-009', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-002', 'SELL-END_USER_COMPUTING_AND_DIGITAL_WORKPLACE-009', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["alternate"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-005', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-001', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-006', 'SELL-SERVERS_AND_COMPUTE_INFRASTRUCTURE-001', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["alternate"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active'),
 ('BOM-019', 'SELL-STORAGE_AND_DATA_PROTECTION-001', 'CATALOGUE_2026_V1', 'V1', '{"selected_options":["standard"]}', '1', '2026-01-01T00:00:00Z', NULL, 'active');

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
 ('BOM-005-1', 'BOM-005', 'COMP-COMPUTE-004', '1', '0', NULL, '0', TRUE),
 ('BOM-005-2', 'BOM-005', 'COMP-STORAGE-003', '2', '1', NULL, '0', TRUE),
 ('BOM-005-3', 'BOM-005', 'COMP-NETWORK_AND_POWER-003', '1', '0', NULL, '0', TRUE),
 ('BOM-005-4', 'BOM-005', 'COMP-CHASSIS_AND_OTHER-002', '1', '0', NULL, '0', TRUE),
 ('BOM-006-1', 'BOM-006', 'COMP-COMPUTE-005', '1', '0', NULL, '0', TRUE),
 ('BOM-006-2', 'BOM-006', 'COMP-STORAGE-004', '2', '1', NULL, '0', TRUE),
 ('BOM-006-3', 'BOM-006', 'COMP-NETWORK_AND_POWER-004', '1', '0', NULL, '0', TRUE),
 ('BOM-006-4', 'BOM-006', 'COMP-CHASSIS_AND_OTHER-003', '1', '0', NULL, '0', TRUE),
 ('BOM-019-1', 'BOM-019', 'COMP-COMPUTE-010', '1', '0', NULL, '0', TRUE),
 ('BOM-019-2', 'BOM-019', 'COMP-STORAGE-007', '2', '1', NULL, '0', TRUE),
 ('BOM-019-3', 'BOM-019', 'COMP-NETWORK_AND_POWER-007', '1', '0', NULL, '0', TRUE),
 ('BOM-019-4', 'BOM-019', 'COMP-CHASSIS_AND_OTHER-005', '1', '0', NULL, '0', TRUE);

INSERT INTO production_requirements (requirement_id, bom_id, operation_seq, capability_code, resource_type, setup_hours, hours_per_unit, batch_size, status) VALUES
 ('BOM-001-1', 'BOM-001', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-001-2', 'BOM-001', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-002-1', 'BOM-002', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-002-2', 'BOM-002', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-005-1', 'BOM-005', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-005-2', 'BOM-005', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-006-1', 'BOM-006', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-006-2', 'BOM-006', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active'),
 ('BOM-019-1', 'BOM-019', '1', 'assembly', 'workforce', '0.5', '0.5', '4', 'active'),
 ('BOM-019-2', 'BOM-019', '2', 'test', 'equipment', '0.5', '0.5', '4', 'active');


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
    IF product_count <> 3 OR bom_count <> 5 OR component_count <> 19 THEN
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
    WHERE bom_line_id IN ('BOM-001-1', 'BOM-001-2', 'BOM-001-3', 'BOM-001-4', 'BOM-002-1', 'BOM-002-2', 'BOM-002-3', 'BOM-002-4', 'BOM-005-1', 'BOM-005-2', 'BOM-005-3', 'BOM-005-4', 'BOM-006-1', 'BOM-006-2', 'BOM-006-3', 'BOM-006-4', 'BOM-019-1', 'BOM-019-2', 'BOM-019-3', 'BOM-019-4');
    IF bad_count <> 20 THEN
        RAISE EXCEPTION 'selected BOM lines missing from master fixture';
    END IF;

    WITH selected_material AS (
        SELECT h.bom_id, h.finished_product_id,
               sum(l.required_quantity_per_output / h.output_quantity /
                   (1 - l.scrap_pct / 100) * part.standard_cost) AS material
        FROM bom_headers h JOIN bom_lines l USING (bom_id)
          JOIN products part ON part.product_id = l.component_product_id
        WHERE l.bom_line_id IN ('BOM-001-1', 'BOM-001-2', 'BOM-001-3', 'BOM-001-4', 'BOM-002-1', 'BOM-002-2', 'BOM-002-3', 'BOM-002-4', 'BOM-005-1', 'BOM-005-2', 'BOM-005-3', 'BOM-005-4', 'BOM-006-1', 'BOM-006-2', 'BOM-006-3', 'BOM-006-4', 'BOM-019-1', 'BOM-019-2', 'BOM-019-3', 'BOM-019-4')
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
           + CASE WHEN count(*) = 5 THEN 0 ELSE 1 END INTO bad_count FROM rolled;
    IF bad_count <> 0 THEN
        RAISE EXCEPTION 'BOM rollup or shared conservative cost failed in PostgreSQL';
    END IF;
END
$fixture$;
\if :{?phase1c_keep_transaction}
\else
ROLLBACK;
\endif
