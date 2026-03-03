-- ============================================================
-- LOGISTICS FLEET ANALYTICS - SQL ANALYSIS QUERIES
-- Database: SQLite (logistics.db)
-- Tables: 14 relational tables loaded from CSV files
-- ============================================================

-- 1. TOP-LEVEL KPIs
SELECT
    ROUND(SUM(revenue + fuel_surcharge + accessorial_charges) / 1e6, 2) AS total_revenue_M,
    ROUND(SUM(revenue) / COUNT(*), 0) AS avg_load_revenue,
    COUNT(*) AS total_loads
FROM loads;

SELECT COUNT(*) AS active_drivers FROM drivers WHERE employment_status = 'Active';
SELECT COUNT(*) AS active_trucks  FROM trucks  WHERE status = 'Active';

SELECT
    ROUND(AVG(average_mpg), 2)               AS fleet_avg_mpg,
    ROUND(SUM(actual_distance_miles)/1e6, 2) AS total_miles_M,
    ROUND(SUM(fuel_gallons_used)/1e3, 0)     AS total_fuel_K_gallons,
    ROUND(AVG(idle_time_hours), 2)           AS avg_idle_hours_per_trip
FROM trips;

-- 2. REVENUE BY YEAR
SELECT
    strftime('%Y', load_date) AS year,
    COUNT(*) AS loads,
    ROUND(SUM(revenue)/1e6, 2) AS revenue_M,
    ROUND(AVG(revenue), 0) AS avg_revenue_per_load
FROM loads
GROUP BY year ORDER BY year;

-- 3. MONTHLY REVENUE TREND
SELECT
    strftime('%Y-%m', load_date) AS month,
    COUNT(*) AS loads,
    ROUND(SUM(revenue)/1e6, 3) AS revenue_M
FROM loads
GROUP BY month ORDER BY month;

-- 4. TOP 10 CUSTOMERS BY TOTAL REVENUE
SELECT
    c.customer_name, c.customer_type,
    COUNT(l.load_id) AS loads,
    ROUND(SUM(l.revenue + l.fuel_surcharge + l.accessorial_charges)/1e6, 2) AS total_revenue_M,
    ROUND(AVG(l.revenue), 0) AS avg_revenue_per_load
FROM loads l
JOIN customers c ON l.customer_id = c.customer_id
GROUP BY c.customer_id
ORDER BY total_revenue_M DESC LIMIT 10;

-- 5. TOP 10 ROUTES BY REVENUE
SELECT
    r.origin_city || ', ' || r.origin_state || ' -> ' ||
    r.destination_city || ', ' || r.destination_state AS lane,
    COUNT(l.load_id) AS loads,
    ROUND(SUM(l.revenue)/1e3, 1) AS revenue_K,
    ROUND(AVG(l.revenue / t.actual_distance_miles), 2) AS revenue_per_mile,
    ROUND(AVG(t.average_mpg), 2) AS avg_mpg
FROM loads l
JOIN routes r ON l.route_id = r.route_id
JOIN trips  t ON l.load_id  = t.load_id
GROUP BY r.route_id
ORDER BY revenue_K DESC LIMIT 10;

-- 6. LOAD TYPE MIX
SELECT load_type, COUNT(*) AS loads,
    ROUND(SUM(revenue)/1e6, 2) AS revenue_M,
    ROUND(AVG(revenue), 0) AS avg_revenue
FROM loads GROUP BY load_type ORDER BY revenue_M DESC;

-- 7. REVENUE BY BOOKING TYPE
SELECT booking_type, COUNT(*) AS loads,
    ROUND(SUM(revenue)/1e6, 2) AS revenue_M,
    ROUND(AVG(revenue), 0) AS avg_revenue
FROM loads GROUP BY booking_type ORDER BY revenue_M DESC;

-- 8. ON-TIME DELIVERY PERFORMANCE
SELECT event_type, COUNT(*) AS total_events,
    SUM(CASE WHEN on_time_flag = 'True' THEN 1 ELSE 0 END) AS on_time_count,
    ROUND(100.0 * SUM(CASE WHEN on_time_flag = 'True' THEN 1 ELSE 0 END) / COUNT(*), 1) AS on_time_pct,
    ROUND(AVG(detention_minutes), 1) AS avg_detention_min
FROM delivery_events GROUP BY event_type;

-- 9. TOP 10 DRIVERS BY REVENUE
SELECT
    d.first_name || ' ' || d.last_name AS driver, d.employment_status,
    COUNT(t.trip_id) AS trips,
    ROUND(SUM(l.revenue)/1e3, 1) AS revenue_K,
    ROUND(AVG(t.average_mpg), 2) AS avg_mpg,
    ROUND(SUM(t.actual_distance_miles)/1e3, 1) AS total_miles_K
FROM trips t
JOIN drivers d ON t.driver_id = d.driver_id
JOIN loads   l ON t.load_id   = l.load_id
GROUP BY d.driver_id ORDER BY revenue_K DESC LIMIT 10;

-- 10. DRIVER SAFETY - MOST INCIDENTS
SELECT
    d.first_name || ' ' || d.last_name AS driver,
    COUNT(*) AS total_incidents,
    SUM(CASE WHEN preventable_flag = 'True' THEN 1 ELSE 0 END) AS preventable_incidents,
    SUM(CASE WHEN injury_flag = 'True' THEN 1 ELSE 0 END) AS injury_incidents,
    ROUND(SUM(claim_amount), 0) AS total_claims_USD
FROM safety_incidents si
JOIN drivers d ON si.driver_id = d.driver_id
GROUP BY si.driver_id ORDER BY total_incidents DESC LIMIT 10;

-- 11. SAFETY INCIDENTS BY TYPE
SELECT incident_type, COUNT(*) AS incidents,
    ROUND(SUM(claim_amount)/1e3, 1) AS total_claims_K,
    SUM(CASE WHEN preventable_flag = 'True' THEN 1 ELSE 0 END) AS preventable,
    SUM(CASE WHEN injury_flag = 'True' THEN 1 ELSE 0 END) AS injuries
FROM safety_incidents GROUP BY incident_type ORDER BY incidents DESC;

-- 12. FUEL EFFICIENCY BY TRUCK MAKE
SELECT tk.make, COUNT(DISTINCT tk.truck_id) AS truck_count,
    ROUND(AVG(t.average_mpg), 2) AS avg_mpg,
    ROUND(SUM(t.fuel_gallons_used)/1e3, 1) AS total_fuel_K_gal,
    ROUND(SUM(fp.total_cost)/1e6, 2) AS total_fuel_cost_M
FROM trips t
JOIN trucks         tk ON t.truck_id  = tk.truck_id
JOIN fuel_purchases fp ON fp.trip_id  = t.trip_id
GROUP BY tk.make ORDER BY avg_mpg DESC;

-- 13. MAINTENANCE COST BY TYPE
SELECT maintenance_type, COUNT(*) AS events,
    ROUND(SUM(total_cost)/1e3, 1) AS total_cost_K,
    ROUND(AVG(total_cost), 0) AS avg_cost_per_event,
    ROUND(AVG(downtime_hours), 1) AS avg_downtime_hours
FROM maintenance_records GROUP BY maintenance_type ORDER BY total_cost_K DESC;

-- 14. FLEET UTILIZATION BY TRUCK MAKE
SELECT tk.make, COUNT(DISTINCT tk.truck_id) AS trucks,
    ROUND(AVG(m.utilization_rate) * 100, 1) AS avg_utilization_pct,
    ROUND(AVG(m.total_miles), 0) AS avg_monthly_miles,
    ROUND(SUM(m.maintenance_cost)/1e3, 1) AS total_maintenance_K
FROM truck_utilization_metrics m
JOIN trucks tk ON m.truck_id = tk.truck_id
GROUP BY tk.make ORDER BY avg_utilization_pct DESC;

-- 15. REVENUE PER MILE BY ROUTE (Profitability Index)
SELECT
    r.origin_city || ' -> ' || r.destination_city AS lane,
    r.typical_distance_miles,
    ROUND(AVG(l.revenue / t.actual_distance_miles), 2) AS avg_rev_per_mile,
    ROUND(AVG(t.average_mpg), 2) AS avg_mpg,
    COUNT(l.load_id) AS load_count
FROM loads l
JOIN routes r ON l.route_id = r.route_id
JOIN trips  t ON l.load_id  = t.load_id
GROUP BY r.route_id
ORDER BY avg_rev_per_mile DESC LIMIT 15;
