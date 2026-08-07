import unittest

from lambda_src.basic.sql_validator import (
    SqlValidationError,
    validate_sql,
)


ALLOWED = {
    "bedrock.company_financial_metrics",
}


class SqlValidatorTests(unittest.TestCase):

    def test_valid_select(self):
        sql = """
        SELECT ticker, fiscal_year, value
        FROM bedrock.company_financial_metrics
        WHERE ticker = 'AAPL'
        """

        validated = validate_sql(sql, ALLOWED)

        self.assertIn("LIMIT 100", validated)

    def test_valid_cte(self):
        sql = """
        WITH revenue AS (
            SELECT ticker, value
            FROM bedrock.company_financial_metrics
            WHERE metric = 'revenue'
        )
        SELECT ticker, value
        FROM revenue
        """

        validated = validate_sql(sql, ALLOWED)

        self.assertIn("LIMIT 100", validated)

    def test_reject_drop(self):
        with self.assertRaises(SqlValidationError):
            validate_sql(
                "DROP TABLE bedrock.company_financial_metrics",
                ALLOWED,
            )

    def test_reject_multiple_statements(self):
        with self.assertRaises(SqlValidationError):
            validate_sql(
                """
                SELECT * FROM bedrock.company_financial_metrics;
                DELETE FROM bedrock.company_financial_metrics
                """,
                ALLOWED,
            )

    def test_reject_unauthorized_relation(self):
        with self.assertRaises(SqlValidationError):
            validate_sql(
                "SELECT * FROM private.secret_table",
                ALLOWED,
            )

    def test_reject_system_relation(self):
        with self.assertRaises(SqlValidationError):
            validate_sql(
                "SELECT * FROM pg_catalog.pg_user",
                ALLOWED,
            )

    def test_reject_large_limit(self):
        with self.assertRaises(SqlValidationError):
            validate_sql(
                """
                SELECT *
                FROM bedrock.company_financial_metrics
                LIMIT 10000
                """,
                ALLOWED,
            )


if __name__ == "__main__":
    unittest.main()