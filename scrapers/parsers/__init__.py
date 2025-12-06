"""HTML parsers for different real estate directories"""

from .realtor_parser import RealtorParser
from .generic_parser import GenericParser

__all__ = ["RealtorParser", "GenericParser"]
