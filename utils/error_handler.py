import streamlit as st
import traceback
import logging
from typing import Callable

logger = logging.getLogger(__name__)

class AppError(Exception):
    """Base application error with user-friendly messages for the UI."""
    def __init__(self, user_message: str, technical_detail: str = None):
        self.user_message = user_message
        self.technical_detail = technical_detail
        super().__init__(technical_detail or user_message)

def handle_error(func: Callable) -> Callable:
    """
    Decorator for consistent error handling.
    Catches AppError for friendly messages and generic Exceptions for critical failures.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AppError as e:
            logger.warning(f"AppError: {e.technical_detail}")
            st.error(f"⚠️ {e.user_message}")
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            st.error("😞 Something went wrong. The technical details have been logged.")
            # If we are in a dev environment, we could show the traceback here
            if st.session_state.get("debug_mode", False):
                st.code(traceback.format_exc())
        return None
    return wrapper
