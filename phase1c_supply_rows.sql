-- Disposable operational evidence attached to draft workstation BOM-001.
-- Run in the open transaction of phase1c_buildable_master.sql, then roll back.
SET search_path TO deal_desk, public;
INSERT INTO suppliers (supplier_id, supplier_code, supplier_name, country_code, status, order_calendar_json)
VALUES ('SYN-SUP-WORKSTATION', 'SYN-SUP-WORKSTATION', 'Fictional workstation kit supplier', 'NL', 'active',
        '{"working_weekdays":[1,2,3,4,5],"holiday_dates":[],"time_zone":"Europe/Amsterdam"}');
INSERT INTO supplier_items (supplier_item_id, supplier_id, product_id, supplier_sku,
    minimum_order_qty, order_multiple, lead_days_min, lead_days_mode, lead_days_max,
    unit_cost, currency_code, valid_from, valid_to, is_active)
VALUES ('SYN-ITEM-NET-ALT', 'SYN-SUP-WORKSTATION', 'COMP-NETWORK_AND_POWER-002', 'SYN-NET-ALT',
        1, 1, 1, 2, 3, 50, 'EUR', '2026-10-01', NULL, TRUE);
INSERT INTO inventory (inventory_id, product_id, location_id, quantity_on_hand,
    quantity_allocated, snapshot_at) VALUES
 ('SYN-STOCK-COMPUTE', 'COMP-COMPUTE-001', 'WH-EU-CENTRAL', 2, 1, '2026-10-07T09:00:00Z'),
 ('SYN-STOCK-STORAGE', 'COMP-STORAGE-001', 'WH-EU-CENTRAL', 4, 1, '2026-10-07T09:00:00Z'),
 ('SYN-STOCK-NET', 'COMP-NETWORK_AND_POWER-001', 'WH-EU-CENTRAL', 1, 0, '2026-10-07T09:00:00Z'),
 ('SYN-STOCK-ENCLOSURE', 'COMP-CHASSIS_AND_OTHER-001', 'WH-EU-CENTRAL', 1, 0, '2026-10-07T09:00:00Z');
INSERT INTO purchase_orders (purchase_order_id, supplier_id, reference_number, ordered_at,
    confirmed_at, status, destination_location_id)
VALUES ('SYN-PO-NET-ALT', 'SYN-SUP-WORKSTATION', 'SYN-PO-NET-ALT',
        '2026-10-07T07:00:00Z', '2026-10-07T08:00:00Z', 'Confirmed', 'WH-EU-CENTRAL');
INSERT INTO inbound_supply (supply_id, purchase_order_id, product_id, location_id,
    quantity, quantity_allocated, expected_date, confirmed_at, status,
    reference_number, evidence_ref, valid_until)
VALUES ('SYN-INBOUND-NET-ALT', 'SYN-PO-NET-ALT', 'COMP-NETWORK_AND_POWER-002', 'WH-EU-CENTRAL',
        2, 1, '2026-10-08', '2026-10-07T08:00:00Z', 'Confirmed',
        'SYN-INBOUND-NET-ALT', 'SYN-PO-CONFIRMATION', '2026-10-09T08:00:00Z');
INSERT INTO production_capacity (capacity_id, location_id, capability_code, resource_type,
    capacity_date, time_zone, available_capacity_hours, allocated_capacity_hours,
    snapshot_at, status, evidence_ref) VALUES
 ('SYN-CAP-ASM', 'WH-EU-CENTRAL', 'assembly', 'workforce', '2026-10-08',
  'Europe/Berlin', 8, 2, '2026-10-07T09:00:00Z', 'active', 'SYN-CAP-ASM'),
 ('SYN-CAP-TEST', 'WH-EU-CENTRAL', 'test', 'equipment', '2026-10-09',
  'Europe/Berlin', 8, 2, '2026-10-07T09:00:00Z', 'active', 'SYN-CAP-TEST');

DO $supply$
DECLARE bad_count INTEGER;
BEGIN
  SELECT count(*) INTO bad_count FROM bom_lines
  WHERE bom_id = 'BOM-001' AND substitute_group_code = 'NETWORK_OPTION'
    AND component_product_id IN ('COMP-NETWORK_AND_POWER-001', 'COMP-NETWORK_AND_POWER-002');
  IF bad_count <> 2 THEN RAISE EXCEPTION 'workstation network alternatives differ'; END IF;

  -- One build needs one compute kit, ceil(2/0.99)=3 drives,
  -- one selected network/power kit and one enclosure kit at the workshop.
  WITH needed AS (
    SELECT l.component_product_id, ceil(l.required_quantity_per_output /
           h.output_quantity / (1 - l.scrap_pct / 100)) AS units
    FROM bom_lines l JOIN bom_headers h USING (bom_id)
    WHERE h.bom_id = 'BOM-001' AND
          (l.substitute_group_code IS NULL OR l.component_product_id = 'COMP-NETWORK_AND_POWER-001')
  ), stocked AS (
    SELECT n.component_product_id, n.units,
           coalesce(sum(i.quantity_on_hand - i.quantity_allocated)
             FILTER (WHERE i.location_id = 'WH-EU-CENTRAL' AND
                     i.snapshot_at BETWEEN '2026-10-06T12:00:00Z' AND '2026-10-07T12:00:00Z'), 0) AS available
    FROM needed n LEFT JOIN inventory i ON i.product_id = n.component_product_id
    GROUP BY n.component_product_id, n.units
  )
  SELECT count(*) FILTER (WHERE available < units) +
         CASE WHEN count(*) = 4 AND sum(units) = 6 THEN 0 ELSE 1 END
    INTO bad_count FROM stocked;
  IF bad_count <> 0 THEN RAISE EXCEPTION 'workstation component stock coverage differs'; END IF;

  SELECT count(*) INTO bad_count FROM inbound_supply s
    JOIN purchase_orders po USING (purchase_order_id)
    JOIN supplier_items si ON si.supplier_id = po.supplier_id AND si.product_id = s.product_id
  WHERE s.product_id = 'COMP-NETWORK_AND_POWER-002' AND s.location_id = po.destination_location_id
    AND s.status = 'Confirmed' AND po.status = 'Confirmed'
    AND s.quantity - s.quantity_allocated >= 1 AND s.expected_date = '2026-10-08'
    AND s.confirmed_at <= '2026-10-07T12:00:00Z'
    AND s.valid_until > '2026-10-07T12:00:00Z'
    AND si.valid_from <= '2026-10-07' AND si.is_active;
  IF bad_count <> 1 THEN RAISE EXCEPTION 'alternate kit inbound proof differs'; END IF;

  SELECT count(*) INTO bad_count FROM production_requirements r
    JOIN production_capacity c ON c.capability_code = r.capability_code
       AND c.resource_type = r.resource_type
  WHERE r.bom_id = 'BOM-001' AND r.status = 'active'
    AND c.location_id = 'WH-EU-CENTRAL' AND c.status = 'active'
    AND c.time_zone = 'Europe/Berlin'
    AND c.capacity_date = CASE r.operation_seq WHEN 1 THEN '2026-10-08'::date
                                                 WHEN 2 THEN '2026-10-09'::date END
    AND c.snapshot_at BETWEEN '2026-10-06T12:00:00Z' AND '2026-10-07T12:00:00Z'
    AND c.available_capacity_hours - c.allocated_capacity_hours >=
        r.setup_hours + r.hours_per_unit;
  IF bad_count <> 2 THEN RAISE EXCEPTION 'ordered workstation capacity coverage differs'; END IF;
END
$supply$;
ROLLBACK;
