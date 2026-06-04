import datetime
from typing import Any

# Custom exception classes for better error handling
class AiracError(Exception):
    """Base exception for Airac errors."""
    pass

class InvalidIdentifierError(AiracError):
    """Raised when an invalid AIRAC identifier is provided."""
    pass

class InvalidDateError(AiracError):
    """Raised when an invalid date is provided."""
    pass

class DateRangeError(AiracError):
    """Raised when a date is outside the supported range."""
    pass

class Airac:
    """An AIRAC cycle implementation in Python.
    
    This class provides calculations for Aeronautical Information Regulation And Control (AIRAC) cycle identifiers and effective calendar dates.
    It is immutable and thread-safe.
    """
    
    # ICAO DOC 8126, 6th edition (2003); Paragraph 2.6.2 b)
    duration_cycle = datetime.timedelta(days=28)
    # First AIRAC cycle in 1964 (cycle 6401) effective date - minimum valid date
    epoch = datetime.datetime(1964, 1, 16, 0, 0, 0, tzinfo=datetime.timezone.utc)
    # Minimum valid serial number (0 corresponds to cycle 6401)
    MIN_SERIAL = 0
    
    def __init__(self, serial: int):
        """Initialize an AIRAC cycle with a serial number relative to the epoch.
        
        Args:
            serial: The serial number relative to the epoch (1964-01-16)
        
        Raises:
            DateRangeError: If the serial number is below the minimum valid value
        """
        if serial < self.MIN_SERIAL:
            raise DateRangeError(f"AIRAC cycle serial number must be >= {self.MIN_SERIAL} (cycles before 6401 are not supported)")
        self._serial = serial
    
    @property
    def serial(self) -> int:
        """Get the serial number of this AIRAC cycle.
        
        Returns:
            The serial number relative to the epoch
        """
        return self._serial
    
    @property
    def effective(self) -> datetime.datetime:
        """Get the effective date of this AIRAC cycle.
        
        Returns:
            The effective date (UTC)
        """
        return self.epoch + self.duration_cycle * self._serial
    
    @property
    def ordinal(self) -> int:
        """Get the ordinal number of this AIRAC cycle.
        
        Returns:
            The ordinal number (1-14)
        """
        # Calculate ordinal directly without calling from_instant
        # First AIRAC of 1964 (cycle 6401) has serial 0
        fourteens = {1976, 1998, 2020, 2043}
        # Calculate total extra cycles from 1964 to year-1
        extra_cycles = sum(1 for y in range(1964, self.year) if y in fourteens)
        first_serial_of_year = (self.year - 1964) * 13 + extra_cycles
        return self.serial - first_serial_of_year + 1
    
    @property
    def year(self) -> int:
        """Get the year of this AIRAC cycle.
        
        Returns:
            The year
        """
        return self.effective.year
    
    def __str__(self) -> str:
        """Get the short representation of this AIRAC cycle (YYOO).
        
        Returns:
            The short representation
        """
        return f"{self.year % 100:02d}{self.ordinal:02d}"
    
    def to_long_string(self) -> str:
        """Get the verbose representation of this AIRAC cycle (YYOO (effective: YYYY-MM-DD; expires: YYYY-MM-DD)).
        
        Returns:
            The verbose representation
        """
        effective = self.effective.strftime("%Y-%m-%d")
        expires = (self.effective + self.duration_cycle).strftime("%Y-%m-%d")
        return f"{self.__str__()} (effective: {effective}; expires: {expires})"
    
    @classmethod
    def from_instant(cls, instant: datetime.datetime) -> "Airac":
        """Create an instance of Airac from an instant.

        Args:
            instant: The point in time at which the AIRAC cycle of interest was current (UTC)

        Returns:
            An instance of Airac

        Raises:
            InvalidDateError: If the provided datetime is invalid or None
            DateRangeError: If the date is before the minimum supported AIRAC date
        """
        if instant is None:
            raise InvalidDateError("Instant cannot be None")
        if not isinstance(instant, datetime.datetime):
            raise InvalidDateError("Instant must be a datetime.datetime object")
        if instant.tzinfo is None:
            raise InvalidDateError("Instant must be timezone-aware (use UTC)")
        if instant.tzinfo != datetime.timezone.utc:
            raise InvalidDateError("Instant must be in UTC timezone")

        # Check if date is before minimum supported AIRAC date
        if instant < cls.epoch:
            raise DateRangeError(f"Date {instant.strftime('%Y-%m-%d')} is before the minimum supported AIRAC date (1964-01-16)")

        # Calculate serial number
        try:
            seconds_since_epoch = (instant - cls.epoch).total_seconds()
            serial = int(seconds_since_epoch // cls.duration_cycle.total_seconds())
            return cls(serial)
        except Exception as e:
            raise InvalidDateError(f"Error calculating AIRAC cycle from instant: {str(e)}")
    
    @classmethod
    def from_identifier(cls, yyoo: str) -> "Airac":
        """Create an instance of Airac from an identifier (YYOO).

        Args:
            yyoo: The identifier of an AIRAC cycle (YYOO)

        Returns:
            An instance of Airac

        Raises:
            InvalidIdentifierError: If the identifier is invalid or malformed
            DateRangeError: If the year does not support the specified cycle number
        """
        if not isinstance(yyoo, str):
            raise InvalidIdentifierError("AIRAC identifier must be a string")

        if len(yyoo) != 4:
            raise InvalidIdentifierError("AIRAC identifier must be exactly 4 characters long")

        try:
            yy = int(yyoo[:2])
            ordinal = int(yyoo[2:])
        except ValueError:
            raise InvalidIdentifierError("AIRAC identifier must contain only numeric digits")

        if yy < 0 or yy > 99:
            raise InvalidIdentifierError("Year component must be between 00 and 99")
        if ordinal < 1 or ordinal > 14:
            raise InvalidIdentifierError("Cycle number must be between 01 and 14")

        # Convert two-digit year to full year (supporting 1964-2063)
        if yy >= 64:
            year = 1900 + yy
        else:
            year = 2000 + yy

        # Validate year range
        if year < 1964 or year > 2063:
            raise DateRangeError(f"Year {year} is outside the supported range (1964-2063)")

        # Calculate the first serial of the given year directly
        # First AIRAC of 1964 is serial 0 (6401)
        fourteens = {1976, 1998, 2020, 2043}
        # Calculate total extra cycles from 1964 to year-1
        extra_cycles = sum(1 for y in range(1964, year) if y in fourteens)
        first_serial_of_year = (year - 1964) * 13 + extra_cycles
        
        # Calculate the serial for this identifier
        serial = first_serial_of_year + ordinal - 1
        
        # Create the Airac instance
        airac = cls(serial)
        
        # Verify that the year matches (this also validates the ordinal)
        if airac.year != year:
            raise DateRangeError(f"Year {year} does not have {ordinal} cycles (only {airac.ordinal} cycles available)")

        return airac
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Airac):
            return False
        return self.serial == other.serial
    
    def __hash__(self) -> int:
        return hash(self.serial)
    
    def __lt__(self, other: "Airac") -> bool:
        return self.serial < other.serial

    def __le__(self, other: "Airac") -> bool:
        return self == other or self < other
    
    def __repr__(self) -> str:
        return f"Airac(serial={self.serial})"
    
    # Additional methods for compatibility with Java API used in tests
    def get_previous(self) -> "Airac":
        """Get the previous AIRAC cycle."""
        return Airac(self.serial - 1)
    
    def get_next(self) -> "Airac":
        """Get the next AIRAC cycle."""
        return Airac(self.serial + 1)
    
    def get_effective(self) -> datetime.datetime:
        """Get the effective date of this AIRAC cycle."""
        return self.effective
    
    def get_ordinal(self) -> int:
        """Get the ordinal number of this AIRAC cycle."""
        return self.ordinal
    
    def get_year(self) -> int:
        """Get the year of this AIRAC cycle."""
        return self.year
    
    def equals(self, other: Any) -> bool:
        """Check equality with another object."""
        return self == other
    
    def to_string(self) -> str:
        """Get the short representation of this AIRAC cycle (YYOO)."""
        return str(self)
    
    @classmethod
    def from_epoch(cls) -> "Airac":
        """Create an instance of Airac from the epoch.
        
        Returns:
            An instance of Airac representing the first cycle (serial 0)
        """
        return cls(0)