import streamlit as st
import traceback
import logging
from typing import Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)

class AppError(Exception):
    """Base application error with user-friendly messages."""
    def __init__(self, user_message: str, technical_detail: str = None):
        self.user_message = user_message
        self.technical_detail = technical_detail
        super().__init__(technical_detail or user_message)

def handle_error(func: Callable) -> Callable:
    """
    Decorator for consistent error handling across the application.
    Captures AppError for user-friendly messaging and generic Exceptions for critical failures.
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except AppError as e:
            logger.warning(f"AppError occurred: {e.user_message} | Detail: {e.technical_detail}")
            st.error(f"⚠️ {e.user_message}")
            if st.session_state.get("debug_mode", False):
                st.code(traceback.format_exc())
        except Exception as e:
            logger.error(f"Unexpected system error in {func.__name__}: {str(e)}", exc_info=True)
            st.error("😞 Something went wrong. Please check the logs or try again later.")
            if st.session_state.get("debug_mode", False):
                st.code(traceback.format_exc())
        return None
    return wrapper
