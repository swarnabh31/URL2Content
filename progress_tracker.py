import streamlit as st
import time
from dataclasses import dataclass
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProgressStep:
    """Represents a step in the progress tracking process."""
    name: str
    weight: float  # 0.0 to 1.0, portion of total progress

class ProgressTracker:
    """
    Tracks and displays progress for multi-step operations in Streamlit.
    
    Provides visual feedback through progress bar and status text updates.
    """
    
    def __init__(self, steps: List[ProgressStep]):
        """
        Initialize the progress tracker.
        
        Args:
            steps: List of ProgressStep objects defining the workflow
        """
        # Validate that weights sum to approximately 1.0
        total_weight = sum(step.weight for step in steps)
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"Progress step weights sum to {total_weight}, expected ~1.0")
        
        self.steps = steps
        self.current_step = 0
        self.progress_bar = st.progress(0.0)
        self.status_text = st.empty()
        logger.debug(f"ProgressTracker initialized with {len(steps)} steps")
    
    def update(self, step_name: str, message: Optional[str] = None):
        """
        Update progress to a specific step.
        
        Args:
            step_name: Name of the step to advance to
            message: Optional custom status message
        """
        # Find the step index
        step_index = None
        for i, step in enumerate(self.steps):
            if step.name == step_name:
                step_index = i
                break
        
        if step_index is None:
            logger.warning(f"Step '{step_name}' not found in progress tracker")
            return
        
        self.current_step = step_index
        
        # Calculate progress based on completed steps
        progress = sum(step.weight for step in self.steps[:self.current_step + 1])
        progress = min(progress, 0.99)  # Leave room for completion
        
        self.progress_bar.progress(progress)
        
        # Update status text
        display_msg = message or f"⏳ {step_name}..."
        self.status_text.info(display_msg)
        logger.debug(f"Progress updated to step '{step_name}': {progress*100:.1f}%")
    
    def complete(self, message: str = "✅ Complete!"):
        """
        Mark the process as complete.
        
        Args:
            message: Completion message to display
        """
        self.progress_bar.progress(1.0)
        self.status_text.success(message)
        logger.debug("ProgressTracker marked as complete")
        
        # Brief pause then clear UI elements
        time.sleep(0.5)
        self.progress_bar.empty()
        self.status_text.empty()
    
    def reset(self):
        """Reset the progress tracker to initial state."""
        self.current_step = 0
        self.progress_bar.progress(0.0)
        self.status_text.empty()
        logger.debug("ProgressTracker reset to initial state")

# Convenience functions for common workflows
def create_content_generation_tracker() -> ProgressTracker:
    """Create a standard progress tracker for content generation workflow."""
    steps = [
        ProgressStep("extract", 0.15),   # Transcript extraction
        ProgressStep("analyze", 0.10),   # Content analysis/strategy selection
        ProgressStep("generate", 0.60),  # LLM content generation
        ProgressStep("format", 0.15),    # Formatting and post-processing
    ]
    return ProgressTracker(steps)

def create_transcript_processing_tracker() -> ProgressTracker:
    """Create a progress tracker for transcript processing only."""
    steps = [
        ProgressStep("validate", 0.1),   # URL validation
        ProgressStep("extract", 0.6),    # Transcript extraction
        ProgressStep("cache", 0.2),      # Caching operations
        ProgressStep("ready", 0.1),      # Ready for next step
    ]
    return ProgressTracker(steps)