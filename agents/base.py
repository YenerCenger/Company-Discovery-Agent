from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Any
from sqlmodel import Session
import structlog

# Type variables for generic agent inputs and outputs
InputT = TypeVar('InputT')
OutputT = TypeVar('OutputT')


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """
    Base agent class with template method pattern

    All agents inherit from this class and implement the process() method.
    The execute() method provides common error handling and logging.
    """

    def __init__(self, db_session: Session, logger: structlog.stdlib.BoundLogger = None):
        """
        Initialize agent

        Args:
            db_session: Database session for persistence
            logger: Structured logger (will create if not provided)
        """
        self.db = db_session
        self.logger = logger or structlog.get_logger(self.__class__.__name__)

    @abstractmethod
    def process(self, input_data: InputT) -> List[OutputT]:
        """
        Core processing logic - must be implemented by subclasses

        Args:
            input_data: Input data for the agent

        Returns:
            List of output objects
        """
        pass

    def execute(self, input_data: InputT) -> List[OutputT]:
        """
        Template method with error handling & logging

        This method:
        1. Logs the start of agent execution
        2. Calls the process() method implemented by subclass
        3. Logs successful completion
        4. Handles and logs any errors
        5. Returns the results

        Args:
            input_data: Input data for the agent

        Returns:
            List of output objects

        Raises:
            Exception: Re-raises any exception from process() after logging
        """
        agent_name = self.__class__.__name__

        self.logger.info(
            f"{agent_name} starting",
            input_data=str(input_data)[:200]  # Truncate long inputs
        )

        try:
            results = self.process(input_data)

            self.logger.info(
                f"{agent_name} completed successfully",
                result_count=len(results) if results else 0
            )

            return results

        except Exception as e:
            self.logger.error(
                f"{agent_name} failed",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            raise

    def _commit_changes(self) -> None:
        """
        Commit database changes

        Helper method for agents that need to explicitly commit
        during processing (not usually needed with context managers)
        """
        try:
            self.db.commit()
        except Exception as e:
            self.logger.error("Failed to commit database changes", error=str(e))
            self.db.rollback()
            raise
