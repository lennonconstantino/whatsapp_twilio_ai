
from pydantic import BaseModel


class ReportSchema(BaseModel):
    report: str

    def report_function(self) -> str:
        """
        Returns the report string.

        Returns:
            str: The report string.
        """
        return self.report
