WITH periodo_actual AS (
    SELECT DISTINCT cod_cia
    FROM datos_balance
    WHERE periodo = '202404'
),
periodo_anterior AS (
    SELECT DISTINCT cod_cia
    FROM datos_balance
    WHERE periodo = '202403'
)
SELECT a.cod_cia
FROM periodo_anterior a
LEFT JOIN periodo_actual b ON a.cod_cia = b.cod_cia
WHERE b.cod_cia IS NULL;