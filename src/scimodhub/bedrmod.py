import logging
import re
from abc import ABC, abstractmethod
from typing import TextIO, Optional, Generator, Generic, TypeVar

from pydantic import ValidationError

from scimodhub.models import EufRecord

logger = logging.getLogger(__name__)


RECORD_TYPE = TypeVar("RECORD_TYPE")


class BedImportEmptyFile(Exception):
    pass


class BedImportTooManyErrors(Exception):
    pass


class TextFileReaderError(Exception):
    pass


class TextFileReader:
    """Provide a text file reader."""

    def __init__(
        self,
        stream: TextIO,
        source: str = "input_stream",
    ):
        self._stream = stream
        self._source = source
        self._line_number = 0

    def read_lines(self) -> Generator[str, None, None]:
        """Read lines.

        :return: All lines in stream.
        :rtype: Generator
        """
        for line in self._stream:
            self._line_number += 1
            stripped_line = line.strip()
            yield stripped_line

    def report_error(self, message: str) -> None:
        """Report reading error.

        :param message: Error message.
        :type message: str
        :raises TextFileReaderError: If failed to read stream.
        """
        raise TextFileReaderError(
            f"{self._source}, line {self._line_number}: {message}"
        )

    def report_error_pydantic_error(self, error: ValidationError) -> None:
        """Report validation error.

        :param error: Pydantic validation error
        :type error: ValidationError
        """
        message = "; ".join(
            [f"{'/'.join(list(e['loc']))}: {e['msg']}" for e in error.errors()]  # type: ignore
        )
        self.report_error(message)


class AbstractBedImporter(Generic[RECORD_TYPE], ABC):
    """Abstract base class to read BED-formatted files."""

    BED_HEADER_REGEXP = re.compile(r"\A#\s*([a-zA-Z_]+)\s*=\s*(.*?)\s*\Z")
    MAX_ERRORS_TO_REPORT = 5

    def __init__(
        self,
        stream: TextIO,
        source: str = "input stream",
        max_error_rate: Optional[float] = 0.05,
    ):
        self._headers: dict[str, str] = {}
        self._error_count = 0
        self._record_count = 0
        self._error_text = ""

        self._source = source
        self._max_error_rate = max_error_rate

        self._reader = TextFileReader(stream=stream, source=source)
        self._line_iterator = self._reader.read_lines()
        self._next_record = (
            self._get_next_record()
        )  # Bootstrap iterator to force parsing of header records

    @abstractmethod
    def get_record_from_fields(self, fields: list[str]) -> RECORD_TYPE:
        pass

    def get_header(self, name: str) -> Optional[str]:
        if name in self._headers:
            return self._headers[name]
        else:
            return None

    def parse(self) -> Generator[RECORD_TYPE, None, None]:
        record = self._next_record
        while record is not None:
            yield record
            record = self._get_next_record()

        if (
            self._max_error_rate is not None
            and self._error_count > self._record_count * self._max_error_rate
        ):
            msg = (
                f"Found too many errors in {self._source} "
                f"(valid: {self._record_count}, errors: {self._error_count})"
            )
            logger.error(msg)
            raise BedImportTooManyErrors(msg)
        if self._record_count == 0:
            msg = f"Did not find any records in '{self._source}'"
            logger.error(msg)
            raise BedImportEmptyFile(msg)

    def get_error_summary(self) -> str:
        if self._error_count == 0:
            return "No errors"
        elif self._error_count <= self.MAX_ERRORS_TO_REPORT:
            return self._error_text
        else:
            return f"""{self._error_text}
            ...
            ({self._error_count} errors in total)
            """

    def report_error(self, message: str):
        try:
            self._reader.report_error(message)
        except TextFileReaderError as err:
            self._error_count += 1
            self._record_count -= 1
            if self._error_count <= self.MAX_ERRORS_TO_REPORT:
                self._error_text += str(err).strip() + "\n"
            logger.warning(str(err))

    def _get_next_record(self):
        try:
            while True:
                line = self._line_iterator.__next__()
                if line.startswith("#"):
                    self._handle_comment(line)
                    continue
                if line == "":
                    continue
                record = self._get_record_from_line(line)
                if record is not None:
                    self._record_count += 1
                    return record
        except StopIteration:
            return None

    def _handle_comment(self, line):
        if self._record_count == 0:  # We are parsing the header
            match = self.BED_HEADER_REGEXP.match(line)
            if match is not None:
                key = match.group(1)
                if key not in self._headers:
                    self._headers[key] = match.group(2)

    def _get_record_from_line(self, line):
        try:
            try:
                fields = [x.strip() for x in line.split("\t")]
                record = self.get_record_from_fields(fields)
                return record
            except ValidationError as err:
                self._reader.report_error_pydantic_error(err)
            except ValueError as err:
                self._reader.report_error(str(err))
        except TextFileReaderError as err:
            self._error_count += 1
            if self._error_count <= self.MAX_ERRORS_TO_REPORT:
                self._error_text += str(err).strip() + "\n"
            logger.warning(str(err))
        return None


class EufImporter(AbstractBedImporter[EufRecord]):
    """EUF importer."""

    def get_record_from_fields(self, fields):
        """Definition of importer."""
        if len(fields) < 11:
            self._reader.report_error(f"Expected 11 fields, but got {len(fields)}")
        return EufRecord(
            chrom=fields[0],
            start=fields[1],
            end=fields[2],
            name=fields[3],
            score=fields[4],
            strand=fields[5],
            thick_start=fields[6],
            thick_end=fields[7],
            item_rgb=fields[8],
            coverage=fields[9],
            frequency=fields[10],
        )
