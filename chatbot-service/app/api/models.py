"""Pydantic models for API request and response validation."""

from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    """
    Request model for AICCRA chatbot conversations.
    
    This model defines the required parameters for interacting with the
    AI-powered AICCRA chatbot.
    """

    message: str = Field(
        ...,
        description="""
        User message or question to send to the AICCRA chatbot.
        
        You can ask about:
        - AICCRA activities, deliverables, and contributions
        - Climate information services and early warning systems
        - Agricultural technologies and farming practices
        - Institutional capacity building and partnerships
        - Project outcomes and impact metrics
        - Data analysis and insights from AICCRA reports
        
        Examples:
        - "What progress has been made on IPI 1.1 in 2025?"
        - "Show me deliverables from the Western Africa cluster"
        - "What innovations were developed for climate-smart agriculture?"
        """,
        min_length=1,
        max_length=2000,
        examples=[
            "What progress has been made on IPI 1.1 in 2025?",
            "Show me deliverables from the Western Africa cluster",
            "What innovations were developed for climate-smart agriculture?"
        ]
    )
    
    phase: Optional[str] = Field(
        default="All phases",
        description="""
        Filter by reporting phase (optional).
        
        Available phases:
        - "All phases" (default)
        - "AWPB 2021", "Progress 2021", "AR 2021"
        - "AWPB 2022", "Progress 2022", "AR 2022"
        - "AWPB 2023", "Progress 2023", "AR 2023"
        - "AWPB 2024", "Progress 2024", "AR 2024"
        - "AWPB 2025", "Progress 2025", "AR 2025"
        """,
        examples=["All phases", "Progress 2025", "AR 2024"]
    )
    
    indicator: Optional[str] = Field(
        default="All indicators",
        description="""
        Filter by AICCRA indicator (optional).
        
        IPI Indicators (Intermediate Performance):
        - IPI 1.1-1.4: Climate information services and early warning systems
        - IPI 2.1-2.3: Agricultural technologies and farming practices  
        - IPI 3.1-3.4: Institutional capacity building and partnerships
        
        PDO Indicators (Project Development Objective):
        - PDO Indicator 1-5: Project outcome and impact metrics
        """,
        examples=["All indicators", "IPI 1.1", "PDO Indicator 1"]
    )
    
    section: Optional[str] = Field(
        default="All sections",
        description="""
        Filter by data section type (optional).
        
        Available sections:
        - "All sections" (default)
        - "Deliverables": Research outputs and publications
        - "OICRs": Outcome Impact Case Reports
        - "Innovations": Technology and practice developments
        - "Contributions": Cluster activities and progress reports
        """,
        examples=["All sections", "Deliverables", "Innovations"]
    )
    
    session_id: str = Field(
        ...,
        description="""
        Unique session identifier for conversation continuity (required).
        
        This is a unique identifier that groups multiple messages in a single conversation session.
        Each new conversation should generate a new unique session_id (e.g., UUID).
        The frontend application must provide this identifier to maintain conversation context.
        """,
        min_length=1,
        examples=["550e8400-e29b-41d4-a716-446655440000", "chat_session_2024_001", "conv_12345_abcde"]
    )
    
    memory_id: str = Field(
        ...,
        description="""
        User email address for personalized knowledge base access (required).
        
        This should be the email address of the user interacting with the chatbot.
        It's used to provide personalized access to the knowledge base and maintain
        user-specific conversation history and preferences.
        """,
        min_length=1,
        examples=["user@example.com", "researcher@cgiar.org", "john.doe@university.edu"]
    )

    insert_data: Optional[bool] = Field(
        default=False,
        description="""
        Force data reload into the knowledge base (optional).
        
        When set to True, the system will:
        - Reload all AICCRA data from the SQL Server database
        - Process and upload fresh data to the AWS Bedrock Knowledge Base
        - Synchronize the knowledge base with the latest information
        
        ⚠️ **Warning**: This operation can take several minutes to complete as it involves:
        - Querying multiple database views
        - Processing thousands of records
        - Uploading files to S3
        - Synchronizing the knowledge base
        
        **When to use**:
        - After significant database updates
        - When troubleshooting data inconsistencies
        - For periodic maintenance (recommended weekly)
        
        **Default**: False (uses existing knowledge base data)
        """,
        examples=[False, True]
    )


class ChatResponse(BaseModel):
    """
    Successful response model for AICCRA chatbot conversations.
    
    Contains the chatbot's response and conversation metadata.
    """
    
    message: str = Field(
        ..., 
        description="""
        Chatbot response message in markdown format.
        
        The response may include:
        - Data-driven insights with proper citations
        - Links to relevant documents and reports
        - Quantitative analysis and progress summaries
        - Contextual explanations of AICCRA activities
        """,
        examples=[
            "Based on the latest data, AICCRA has achieved significant progress on IPI 1.1 in 2025. The **Western Africa** cluster has contributed 45% of the total achievements..."
        ]
    )
    
    session_id: str = Field(
        ..., 
        description="Session ID for this conversation",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    
    filters_applied: dict = Field(
        ...,
        description="Summary of filters that were applied to this query",
        examples=[{
            "phase": "Progress 2025",
            "indicator": "IPI 1.1", 
            "section": "All sections"
        }]
    )

    data_reloaded: Optional[bool] = Field(
        default=None,
        description="Indicates if fresh data was loaded into the knowledge base for this request",
        examples=[False, True]
    )

    processing_info: Optional[dict] = Field(
        default=None,
        description="Additional processing information when data reload was performed",
        examples=[{
            "data_reload_time": "45.2s",
            "records_processed": 15847,
            "tables_updated": ["deliverables", "contributions", "innovations", "oicrs", "questions"]
        }]
    )
    
    status: str = Field(
        default="success", 
        description="Response status indicator",
        examples=["success"]
    )


class ErrorResponse(BaseModel):
    """
    Error response model for failed requests.
    
    Provides detailed error information to help with troubleshooting.
    """
    
    error: str = Field(
        ..., 
        description="Brief error message describing what went wrong",
        examples=[
            "Invalid request parameters",
            "Chatbot service unavailable", 
            "AWS Bedrock service error",
            "Context limit exceeded",
            "Data reload failed"
        ]
    )
    
    status: str = Field(
        default="error", 
        description="Response status indicator",
        examples=["error"]
    )

    details: Optional[str] = Field(
        None, 
        description="Additional error details for troubleshooting",
        examples=[
            "Message length exceeds maximum allowed characters",
            "Invalid session ID format",
            "AWS service temporarily unavailable",
            "Database connection failed during data reload"
        ]
    )