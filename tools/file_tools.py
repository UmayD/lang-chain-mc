"""
LangChain tools for file operations in the workspace.
These tools work on the shared workspace directory.
"""
from pathlib import Path
from typing import Literal, Optional
from langchain_core.tools import tool
import logging

from utils.settings import WORKSPACE_DIR
from database.db import db_manager

# Setup logging
logger = logging.getLogger(__name__)


# Original functions (for direct use - without tool decorator)
def create_file_func(filename: str, content: str, session_id: Optional[str] = None) -> str:
    """
    Creates a new file in the workspace.
    
    Args:
        filename: Name of the file to create (e.g., "summary.md")
        content: Content to write to the file
        session_id: Optional session ID for database tracking (default: None)
    
    Returns:
        Success message
    """
    file_path = WORKSPACE_DIR / filename
    
    # Create workspace directory if it doesn't exist
    WORKSPACE_DIR.mkdir(exist_ok=True)
    
    # Create file and write content
    file_path.write_text(content, encoding="utf-8")
    
    # Save file metadata to database if session_id is provided
    if session_id:
        try:
            file_size = file_path.stat().st_size
            file_type = file_path.suffix.lstrip('.') or 'unknown'
            relative_path = str(file_path.relative_to(WORKSPACE_DIR))
            
            db_manager.save_file_metadata(
                session_id=session_id,
                filename=filename,
                file_path=relative_path,
                file_size=file_size,
                file_type=file_type,
                description=None,
                execution_id=None  # File agent'lar için None
            )
            logger.info(f"File metadata saved to database: {filename} (session_id: {session_id})")
        except Exception as e:
            # Log error but don't fail file creation
            logger.warning(f"Failed to save file metadata to database: {e}")
    
    return f"File created successfully: {file_path}"


def read_file_func(filename: str) -> str:
    """
    Reads a file from the workspace.
    
    Args:
        filename: Name of the file to read (e.g., "summary.md")
    
    Returns:
        File content (string) or error message
    """
    file_path = WORKSPACE_DIR / filename
    
    if not file_path.exists():
        return f"Error: File not found: {file_path}"
    
    try:
        content = file_path.read_text(encoding="utf-8")
        return content
    except Exception as e:
        return f"Error: Could not read file: {str(e)}"


def update_file_func(filename: str, content: str, mode: Literal["overwrite", "append"] = "overwrite", session_id: Optional[str] = None) -> str:
    """
    Updates a file in the workspace.
    
    Args:
        filename: Name of the file to update (e.g., "summary.md")
        content: New content to write
        mode: "overwrite" (overwrite) or "append" (append)
        session_id: Optional session ID for database tracking (default: None)
    
    Returns:
        Success message or error message
    """
    file_path = WORKSPACE_DIR / filename
    
    if not file_path.exists():
        return f"Error: File not found: {file_path}"
    
    try:
        if mode == "append":
            # Read existing content and append new content
            existing_content = file_path.read_text(encoding="utf-8")
            new_content = existing_content + "\n\n" + content
            file_path.write_text(new_content, encoding="utf-8")
        else:
            # Overwrite mode
            file_path.write_text(content, encoding="utf-8")
        
        # Update edited_at timestamp in database if session_id is provided
        if session_id:
            try:
                file_size = file_path.stat().st_size
                db_manager.update_file_edited_at(
                    session_id=session_id,
                    filename=filename,
                    file_size=file_size
                )
                logger.info(f"File edited_at updated in database: {filename} (session_id: {session_id})")
            except Exception as e:
                # Log error but don't fail file update
                logger.warning(f"Failed to update file edited_at in database: {e}")
        
        return f"File updated successfully ({mode}): {file_path}"
    except Exception as e:
        return f"Error: Could not update file: {str(e)}"


# LangChain tools (for agents - with @tool decorator)
@tool
def create_file(filename: str, content: str) -> str:
    """
    Creates a new file in the workspace.
    
    Use this tool to create markdown files or other text files in the workspace directory.
    
    Args:
        filename: Name of the file to create (e.g., "summary.md")
        content: Content to write to the file
    
    Returns:
        Success message confirming file creation
    """
    return create_file_func(filename, content, None)


@tool
def read_file(filename: str) -> str:
    """
    Reads a file from the workspace.
    
    Use this tool to read existing files from the workspace directory.
    
    Args:
        filename: Name of the file to read (e.g., "summary.md")
    
    Returns:
        File content as a string, or an error message if file not found
    """
    return read_file_func(filename)


@tool
def update_file(filename: str, content: str, mode: Literal["overwrite", "append"] = "overwrite") -> str:
    """
    Updates a file in the workspace.
    
    Use this tool to modify existing files. You can either overwrite the entire file
    or append new content to it.
    
    Args:
        filename: Name of the file to update (e.g., "summary.md")
        content: New content to write
        mode: "overwrite" to replace entire file, or "append" to add content at the end (default: "overwrite")
    
    Returns:
        Success message confirming file update, or error message if file not found
    """
    return update_file_func(filename, content, mode, None)


# Export all tools as a list (for agents)
FILE_TOOLS = [create_file, read_file, update_file]


def get_file_tools(session_id: Optional[str] = None):
    """
    Returns a list of file operation tools for use in agents.
    
    Args:
        session_id: Optional session ID to bind to create_file and update_file tools for database tracking
    
    Returns:
        List of LangChain tools for file operations
    """
    if session_id:
        # Create wrapper tools with session_id bound
        @tool
        def create_file_with_session(filename: str, content: str) -> str:
            """
            Creates a new file in the workspace.
            
            Use this tool to create markdown files or other text files in the workspace directory.
            
            Args:
                filename: Name of the file to create (e.g., "summary.md")
                content: Content to write to the file
            
            Returns:
                Success message confirming file creation
            """
            return create_file_func(filename, content, session_id)
        
        @tool
        def update_file_with_session(filename: str, content: str, mode: Literal["overwrite", "append"] = "overwrite") -> str:
            """
            Updates a file in the workspace.
            
            Use this tool to modify existing files. You can either overwrite the entire file
            or append new content to it.
            
            Args:
                filename: Name of the file to update (e.g., "summary.md")
                content: New content to write
                mode: "overwrite" to replace entire file, or "append" to add content at the end (default: "overwrite")
            
            Returns:
                Success message confirming file update, or error message if file not found
            """
            return update_file_func(filename, content, mode, session_id)
        
        return [create_file_with_session, read_file, update_file_with_session]
    return FILE_TOOLS
