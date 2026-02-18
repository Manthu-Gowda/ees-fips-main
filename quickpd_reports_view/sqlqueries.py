approved_date_analysis_graph_query = """
WITH date_series AS (
    SELECT generate_series(
        %s::date,
        %s::date,
        interval '1 day'
    )::date AS approved_date
),
approved_data AS (
    SELECT 
        DATE(COALESCE(sm."originalTimeApp", sm."timeApp")) AS approved_date,
        COUNT(DISTINCT c."citationID") AS total_approved,
        COUNT(DISTINCT pcd."citationID") AS total_paid,
        COUNT(DISTINCT c."citationID") FILTER (WHERE pcd."citationID" IS NULL) AS total_unpaid,
        COALESCE(SUM(pcd.paid_amount), 0) AS amount_received
    FROM sup_metadata sm
    JOIN citation c ON sm.citation_id = c.id
    LEFT JOIN paid_citations pcd ON pcd."citationID" = c."citationID"
    WHERE sm."isApproved" = TRUE
    AND (
            COALESCE(sm."originalTimeApp", sm."timeApp") < DATE '2025-12-01'
        OR (
                COALESCE(sm."originalTimeApp", sm."timeApp") >= DATE '2025-12-01'
                AND sm."isEdited" = FALSE
                AND sm."isMailCitationRejected" = FALSE
            )
        OR (
            COALESCE(sm."originalTimeApp", sm."timeApp") >= DATE '2026-01-01'
            )
        )
      AND c.station_id = %s
      AND DATE(COALESCE(sm."originalTimeApp", sm."timeApp")) BETWEEN %s::date AND %s::date
    GROUP BY DATE(COALESCE(sm."originalTimeApp", sm."timeApp"))
)
SELECT
    ds.approved_date,
    EXTRACT(YEAR FROM ds.approved_date)::text AS year,
    TO_CHAR(ds.approved_date, 'FMMonth') AS month,
    TO_CHAR(ds.approved_date, 'FMMonth DD YYYY') AS approvedDate,
    COALESCE(ad.total_approved, 0) AS totalApproved,
    COALESCE(ad.total_paid, 0) AS paid,
    COALESCE(ad.total_approved, 0) - COALESCE(ad.total_paid, 0) AS unPaid,
    CASE 
        WHEN ad.total_approved > 0 
        THEN ROUND((ad.total_paid::numeric / ad.total_approved::numeric) * 100, 2)
        ELSE 0
    END AS paidPercentage,
    CASE 
        WHEN ad.total_approved > 0 
        THEN ROUND(100 - ((ad.total_paid::numeric / ad.total_approved::numeric) * 100), 2)
        ELSE 0
    END AS unPaidPercentage,
    ad.amount_received AS amountReceived,
    0 AS amountDues
FROM date_series ds
LEFT JOIN approved_data ad ON ds.approved_date = ad.approved_date
ORDER BY ds.approved_date;
"""