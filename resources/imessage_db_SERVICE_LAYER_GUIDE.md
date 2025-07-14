# iMessage Database - Service Layer & Database Schema Developer Guide

## Table of Contents
- [Service Layer Architecture](#service-layer-architecture)
- [Database Schema Reference](#database-schema-reference)
- [Quick Start Guide](#quick-start-guide)
- [Service Layer API](#service-layer-api)
- [Integration Patterns](#integration-patterns)
- [Error Handling](#error-handling)

---

## Service Layer Architecture

### Overview
The service layer implements clean architecture principles with business logic separated from data access. All database operations go through repositories, while services handle validation, orchestration, and cross-service coordination.

### Core Services

#### UserService (`imessage_db/services/user.py:16`)
Manages user accounts with simplified phone number handling for international support.

**Phone Number Processing:**
- Strips all non-digits from input
- Validates minimum 7 digits
- Treats as unique identifier (no formatting)
- Example: `+1 (555) 123-4567` → `15551234567`

**Key Methods:**
```python
# Get or create user (seamless contact management)
user = await user_service.get_or_create_user(
    phone_number="+1 (555) 123-4567",
    first_name="John",
    email="john@example.com"
)

# Find existing user
user = await user_service.get_user_by_phone("5551234567")

# Update user info
updated_user = await user_service.update_user_info(
    user_id="uuid-here",
    first_name="Johnny",
    display_name="Johnny Doe"
)
```

#### TaskService (`imessage_db/services/task.py:16`)
Handles task lifecycle with strict status transition validation.

**Status Transitions:**
```
PENDING → [IN_PROGRESS, CANCELLED]
IN_PROGRESS → [COMPLETED, CANCELLED]
COMPLETED → [] (final state)
CANCELLED → [] (final state)
```

**Key Methods:**
```python
# Create new task
task = await task_service.create_task(
    user_id="user-uuid",
    title="Review code",
    description="Review the new feature branch",
    priority=TaskPriority.HIGH
)

# Start task (PENDING → IN_PROGRESS)
task = await task_service.start_task(task_id="task-uuid")

# Complete task (IN_PROGRESS → COMPLETED)
task = await task_service.complete_task(
    task_id="task-uuid",
    result="Code reviewed and approved"
)

# Search tasks
tasks = await task_service.search_tasks(
    user_id="user-uuid",
    status=TaskStatus.IN_PROGRESS,
    priority=TaskPriority.HIGH
)
```

#### MessageService (`imessage_db/services/message.py:18`)
Processes messages with automatic user creation and task linking.

**Cross-Service Coordination:**
- Automatically creates new users from phone numbers
- Links messages to tasks for workflow integration
- Manages conversation threading

**Key Methods:**
```python
# Store message (auto-creates user if needed)
message = await message_service.store_message(
    phone_number="+1 (555) 123-4567",
    content="Can you help me with the project?",
    is_from_user=True,
    task_id="task-uuid"  # Optional task linking
)

# Link existing message to task
message = await message_service.link_message_to_task(
    message_id="message-uuid",
    task_id="task-uuid"
)

# Get conversation history
messages = await message_service.get_conversation_history(
    user_id="user-uuid",
    limit=50,
    include_metadata=True
)

# Search message content
results = await message_service.search_messages(
    pattern="project deadline",
    user_id="user-uuid"
)
```

#### AttachmentService (`imessage_db/services/attachment.py:21`)
Handles file storage with proximity search for vector integration.

**File Storage Pattern:**
- Path: `./attachments/YYYY/MM/DD/uuid-filename.ext`
- Automatic directory creation
- File data can be stored as bytes or file path
- Checksum validation for integrity

**Vector Search Integration:**
```python
# Store attachment with message proximity
attachment = await attachment_service.store_attachment(
    filename="document.pdf",
    file_data=pdf_bytes,
    message_id="message-uuid",
    file_type="application/pdf"
)

# Get attachments near a message (for vector search)
nearby_attachments = await attachment_service.get_attachments_near_message(
    target_message_id="message-uuid",
    window_size=10  # Default: 10 messages
)

# Batch retrieval for vector search results
attachments = await attachment_service.get_attachments_for_multiple_messages(
    message_ids=["msg1", "msg2", "msg3"]
)

# Time-based proximity search
attachments = await attachment_service.get_attachments_in_time_window(
    start_time=datetime.now() - timedelta(hours=1),
    end_time=datetime.now()
)
```

### ServiceFactory Pattern (`imessage_db/services/factory.py:20`)

**Dependency Injection:**
```python
from imessage_db import get_db
from imessage_db.services import ServiceFactory

# Manual factory usage
async with get_db() as session:
    factory = ServiceFactory(session, attachment_storage_path="./attachments")
    
    # Services are cached and dependencies auto-resolved
    user_service = factory.get_user_service()
    message_service = factory.get_message_service()  # Gets UserService dependency
    
    # Work with services...
    user = await user_service.get_or_create_user("+1234567890")
    message = await message_service.store_message("+1234567890", "Hello!")
    
    # Cleanup when done
    await factory.cleanup_all_services()
```

**FastAPI Integration:**
```python
from fastapi import Depends, FastAPI
from imessage_db.services.factory import get_user_service, get_message_service

app = FastAPI()

@app.post("/users")
async def create_user(
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.get_or_create_user("+1234567890")

@app.post("/messages")
async def store_message(
    message_service: MessageService = Depends(get_message_service)
):
    return await message_service.store_message("+1234567890", "Hello from API!")
```

---

## Database Schema Reference

### Core Entities

#### User (`imessage_db/models/user.py:9`)
```sql
TABLE users (
    id VARCHAR PRIMARY KEY,           -- UUID string
    phone_number VARCHAR(20) UNIQUE,  -- Digits only, indexed
    email VARCHAR(255) UNIQUE,        -- Optional, indexed
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    display_name VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    preferences JSONB,                -- User preferences/settings
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

#### Task (`imessage_db/models/task.py:25`)
```sql
TABLE tasks (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR REFERENCES users(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    status ENUM('pending', 'in_progress', 'completed', 'failed', 'cancelled'),
    priority ENUM('low', 'medium', 'high', 'urgent'),
    is_recurring BOOLEAN DEFAULT FALSE,
    recurrence_pattern JSONB,         -- Recurring task configuration
    task_metadata JSONB,              -- Additional task data
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

#### Message (`imessage_db/models/message.py:9`)
```sql
TABLE messages (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR REFERENCES users(id),
    task_id VARCHAR REFERENCES tasks(id),    -- Optional task linking
    content TEXT NOT NULL,
    message_type VARCHAR(50) DEFAULT 'text',
    is_from_user BOOLEAN NOT NULL,
    thread_id VARCHAR(255),                  -- Conversation grouping
    reply_to_id VARCHAR REFERENCES messages(id), -- Reply threading
    sequence_number INTEGER,                 -- Message ordering
    message_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

#### Attachment (`imessage_db/models/attachment.py:9`)
```sql
TABLE attachments (
    id VARCHAR PRIMARY KEY,
    message_id VARCHAR REFERENCES messages(id),  -- Optional
    task_id VARCHAR REFERENCES tasks(id),        -- Optional
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(100) NOT NULL,
    file_size INTEGER NOT NULL,
    file_path VARCHAR(500),                      -- Storage path
    file_data BYTEA,                            -- Or direct bytes
    mime_type VARCHAR(100) NOT NULL,
    checksum VARCHAR(64),                       -- File integrity
    attachment_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

#### TaskContext (`imessage_db/models/task_context.py:10`)
```sql
TABLE task_contexts (
    id VARCHAR PRIMARY KEY,
    task_id VARCHAR REFERENCES tasks(id),
    context_type VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536),                     -- pgvector for AI
    source VARCHAR(255),                        -- Context source
    context_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

### Entity Relationships

```
User (1) ──→ (many) Task
User (1) ──→ (many) Message
Task (1) ──→ (many) Message [optional]
Task (1) ──→ (many) TaskContext
Task (1) ──→ (many) Attachment [optional]
Message (1) ──→ (many) Attachment [optional]
Message (1) ──→ (1) Message [reply_to, optional]
```

**Flexible Design Notes:**
- Messages can exist without tasks (general chat)
- Attachments can link to messages, tasks, both, or neither
- Task contexts store vector embeddings for AI features
- All entities use UUID primary keys for distribution

---

## Quick Start Guide

### Basic Usage Pattern

```python
from imessage_db import get_db
from imessage_db.services import ServiceFactory
from imessage_db.models import TaskPriority, TaskStatus

async def process_imessage(phone_number: str, content: str):
    """Example: Process incoming iMessage"""
    async with get_db() as session:
        factory = ServiceFactory(session)
        
        # Get services (auto-dependency injection)
        user_service = factory.get_user_service()
        message_service = factory.get_message_service()
        task_service = factory.get_task_service()
        
        try:
            # Store message (auto-creates user if needed)
            message = await message_service.store_message(
                phone_number=phone_number,
                content=content,
                is_from_user=True
            )
            
            # Check if this is task-related
            if "task" in content.lower():
                # Create task from message
                task = await task_service.create_task(
                    user_id=message.user_id,
                    title=f"Task from message: {content[:50]}...",
                    priority=TaskPriority.MEDIUM
                )
                
                # Link message to task
                await message_service.link_message_to_task(
                    message_id=message.id,
                    task_id=task.id
                )
            
            return message
            
        finally:
            await factory.cleanup_all_services()
```

### Error Handling Pattern

```python
from imessage_db.services.exceptions import (
    UserNotFoundError,
    TaskNotFoundError,
    InvalidPhoneNumberError,
    ServiceError
)

async def safe_message_processing(phone_number: str, content: str):
    try:
        return await process_imessage(phone_number, content)
    
    except InvalidPhoneNumberError as e:
        logger.error(f"Invalid phone number {phone_number}: {e}")
        return None
    
    except ServiceError as e:
        logger.error(f"Service error: {e.message}")
        if e.original_error:
            logger.error(f"Original error: {e.original_error}")
        return None
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None
```

---

## Service Layer API

### Service Protocol (`imessage_db/services/base.py:11`)
All services implement this protocol for consistent behavior:

```python
class ServiceProtocol(Protocol):
    async def validate_input(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate and clean input data"""
        
    async def handle_error(self, error: Exception, context: str) -> None:
        """Handle service-specific errors with context"""
        
    async def cleanup_resources(self, session: AsyncSession | None = None) -> None:
        """Clean up service resources"""
```

### Service Dependencies

```python
# Service dependency graph
UserService          # Standalone
TaskService          # Standalone  
MessageService       # → UserService
AttachmentService    # → MessageService (for proximity search)
```

**Dependency Resolution:**
- ServiceFactory automatically resolves dependencies
- All services share the same database session
- Cross-service calls use dependency injection

---

## Integration Patterns

### iMessage Handler Integration
```python
# Example handler for Phase 4
class iMessageHandler:
    def __init__(self, service_factory: ServiceFactory):
        self.message_service = service_factory.get_message_service()
        self.attachment_service = service_factory.get_attachment_service()
    
    async def handle_incoming_message(self, phone: str, content: str, attachments: list[bytes] = None):
        # Store message
        message = await self.message_service.store_message(phone, content, is_from_user=True)
        
        # Process attachments
        if attachments:
            for i, file_data in enumerate(attachments):
                await self.attachment_service.store_attachment(
                    filename=f"attachment_{i}.bin",
                    file_data=file_data,
                    message_id=message.id,
                    file_type="application/octet-stream"
                )
        
        return message
```

### Vector Search Integration
```python
# Example vector search workflow
async def find_related_attachments(query_embedding: list[float], session: AsyncSession):
    factory = ServiceFactory(session)
    attachment_service = factory.get_attachment_service()
    
    # 1. Vector search finds relevant messages (external vector DB)
    relevant_message_ids = await vector_search(query_embedding)
    
    # 2. Get attachments for those messages
    attachments = await attachment_service.get_attachments_for_multiple_messages(
        message_ids=relevant_message_ids
    )
    
    # 3. Get nearby attachments for context
    context_attachments = []
    for message_id in relevant_message_ids[:3]:  # Top 3 matches
        nearby = await attachment_service.get_attachments_near_message(
            target_message_id=message_id,
            window_size=5
        )
        context_attachments.extend(nearby)
    
    return attachments, context_attachments
```

---

## Error Handling

### Service-Specific Exceptions (`imessage_db/services/exceptions.py`)

```python
# Base service error with context preservation
ServiceError("MessageService: store_message failed", original_error=db_error)

# Entity not found errors
UserNotFoundError(user_id="uuid", original_error=repo_error)
TaskNotFoundError(task_id="uuid", original_error=repo_error)
MessageNotFoundError(message_id="uuid", original_error=repo_error)
AttachmentNotFoundError(attachment_id="uuid", original_error=repo_error)

# Validation errors
InvalidPhoneNumberError(phone_number="invalid", original_error=validation_error)

# File operation errors
FileStorageError(operation="write", path="/path/to/file", original_error=os_error)
```

### Error Handling Best Practices

```python
# 1. Always preserve original errors
try:
    result = await repository.create(data)
except SQLAlchemyError as e:
    raise ServiceError("User creation failed", original_error=e)

# 2. Add business context
try:
    task = await task_repo.get_by_id(task_id)
    if not task:
        raise TaskNotFoundError(task_id)
except RepositoryError as e:
    raise TaskNotFoundError(task_id, original_error=e)

# 3. Handle cross-service errors
try:
    user = await user_service.get_or_create_user(phone_number)
    message = await message_repo.create({...})
except InvalidPhoneNumberError:
    raise  # Re-raise service errors as-is
except ServiceError as e:
    raise ServiceError("Message storage failed", original_error=e)
```

---



## Architecture Notes

### Design Principles

**What Services DO:**
- ✅ Business logic and validation
- ✅ Cross-repository coordination
- ✅ Service-to-service communication  
- ✅ Transaction management
- ✅ Error handling with business context
- ✅ Input validation and sanitization

**What Services DON'T Do:**
- ❌ Direct database access (use repositories)
- ❌ HTTP handling (external handlers in Phase 4)
- ❌ File system operations (except AttachmentService storage)
- ❌ External API calls (external handlers)
- ❌ Authentication/authorization (middleware)

### Performance Considerations

- **Service Caching**: ServiceFactory caches service instances
- **Session Sharing**: All services share database session for transaction efficiency
- **Lazy Loading**: Services created only when requested
- **Batch Operations**: AttachmentService supports batch retrieval for vector search
