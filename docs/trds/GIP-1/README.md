# Requirements Document

## Introduction

This document specifies requirements for a real-time collaborative rich-text editor MVP that enables 10-20 concurrent users to simultaneously edit structured documents with low-latency synchronization. The system uses ProseMirror for editing, Yjs for conflict-free state synchronization, WebSocket-based real-time communication, and MongoDB for persistence.

## Glossary

- **Editor**: The ProseMirror-based rich-text editing component in the React frontend
- **Shared_Document**: The Yjs CRDT data structure representing the collaborative document state
- **WebSocket_Server**: The Python backend service handling real-time message broadcasting
- **Document_Store**: The MongoDB database storing document snapshots and update history
- **Client**: A user's browser session connected to the Editor
- **Update**: A Yjs binary message representing incremental changes to the Shared_Document
- **Snapshot**: A complete serialized state of a document at a specific point in time
- **Slash_Command**: A command palette triggered by typing "/" in the Editor
- **Mention**: A reference to a user inserted via "@username" syntax
- **Node**: A structural element in the ProseMirror document schema (paragraph, heading, etc.)

## Requirements

### Requirement 1: Document Creation and Retrieval

**User Story:** As a user, I want to create and retrieve documents, so that I can start editing and access existing content.

#### Acceptance Criteria

1. WHEN a user requests document creation, THE Document_Store SHALL create a new document record with a unique identifier
2. WHEN a user requests a document by identifier, THE Document_Store SHALL return the document metadata and latest Snapshot
3. WHEN a user requests a non-existent document, THE WebSocket_Server SHALL return an error response within 200ms
4. THE Document_Store SHALL store document metadata including document identifier, creation timestamp, and last modified timestamp
5. WHEN a document list is requested, THE Document_Store SHALL return all document metadata ordered by last modified timestamp

### Requirement 2: Real-Time Document Synchronization

**User Story:** As a user, I want my edits to appear on other users' screens in real-time, so that we can collaborate effectively.

#### Acceptance Criteria

1. WHEN a Client generates an Update, THE Client SHALL send the Update to the WebSocket_Server via WebSocket connection
2. WHEN the WebSocket_Server receives an Update, THE WebSocket_Server SHALL broadcast the Update to all connected Clients for that document within 200ms
3. WHEN a Client receives an Update, THE Client SHALL apply the Update to its local Shared_Document
4. THE Shared_Document SHALL merge concurrent edits from multiple Clients without conflicts using Yjs CRDT algorithms
5. WHEN network latency exceeds 200ms, THE Client SHALL continue accepting local edits and queue Updates for transmission

### Requirement 3: WebSocket Connection Management

**User Story:** As a user, I want reliable connections to the server, so that my edits are not lost during network issues.

#### Acceptance Criteria

1. WHEN a Client requests connection, THE WebSocket_Server SHALL establish a WebSocket connection at endpoint /ws/document/{docId}
2. WHEN a WebSocket connection is established, THE WebSocket_Server SHALL send the current document state to the Client
3. IF a WebSocket connection is interrupted, THEN THE Client SHALL attempt reconnection with exponential backoff starting at 1 second
4. WHEN a Client reconnects, THE WebSocket_Server SHALL send any missed Updates since the Client's last known state
5. WHEN a Client disconnects, THE WebSocket_Server SHALL remove the Client from the broadcast list for that document

### Requirement 4: Rich-Text Editing Capabilities

**User Story:** As a user, I want to format text with various structural elements, so that I can create well-organized documents.

#### Acceptance Criteria

1. THE Editor SHALL support Node types: paragraph, heading (levels 1-3), ordered list, unordered list, table, image, embed, and mention
2. WHEN a user applies formatting, THE Editor SHALL generate a ProseMirror transaction that updates the Shared_Document
3. THE Editor SHALL render all supported Node types with appropriate visual styling
4. WHEN a user edits a table cell, THE Editor SHALL update only the affected cell content in the Shared_Document
5. WHEN a user inserts an image, THE Editor SHALL create an image Node with a URL reference

### Requirement 5: Slash Command Interface

**User Story:** As a user, I want to quickly insert structured elements using slash commands, so that I can efficiently build documents.

#### Acceptance Criteria

1. WHEN a user types "/" at the start of a line or after whitespace, THE Editor SHALL display a command palette
2. THE Editor SHALL provide slash commands: /heading, /list, /table, /image, and /embed
3. WHEN a user selects a slash command, THE Editor SHALL replace the "/" character and insert the corresponding Node type
4. WHEN a user types additional characters after "/", THE Editor SHALL filter the command palette to matching commands
5. WHEN a user presses Escape or clicks outside the palette, THE Editor SHALL close the command palette

### Requirement 6: User Mentions

**User Story:** As a user, I want to mention other users in documents, so that I can reference collaborators and draw their attention.

#### Acceptance Criteria

1. WHEN a user types "@" followed by characters, THE Editor SHALL query the WebSocket_Server for matching usernames
2. THE WebSocket_Server SHALL return user search results within 200ms via GET /users/search?q={query}
3. WHEN the Editor receives search results, THE Editor SHALL display a dropdown list of matching users
4. WHEN a user selects a mention from the dropdown, THE Editor SHALL insert a mention Node with the user's identifier and display name
5. THE Editor SHALL render mention Nodes with distinctive visual styling to differentiate them from regular text

### Requirement 7: Document Persistence

**User Story:** As a system administrator, I want documents to be persisted reliably, so that no data is lost during server restarts.

#### Acceptance Criteria

1. WHEN the WebSocket_Server receives an Update, THE WebSocket_Server SHALL store the Update in the Document_Store with document identifier and version number
2. THE Document_Store SHALL maintain a documents collection storing document metadata and latest Snapshot
3. THE Document_Store SHALL maintain a document_updates collection storing all Updates with indexed docId and version fields
4. WHEN 100 Updates have been stored for a document, THE WebSocket_Server SHALL generate a new Snapshot and store it in the Document_Store
5. WHEN a Snapshot is created, THE WebSocket_Server SHALL delete Updates older than the Snapshot to prevent unbounded growth

### Requirement 8: Document Loading and Reconstruction

**User Story:** As a user, I want documents to load quickly with all recent changes, so that I can start editing without delay.

#### Acceptance Criteria

1. WHEN a Client requests a document, THE WebSocket_Server SHALL retrieve the latest Snapshot from the Document_Store
2. WHEN a Snapshot exists, THE WebSocket_Server SHALL retrieve all Updates created after the Snapshot from the Document_Store
3. THE WebSocket_Server SHALL send the Snapshot and Updates to the Client in order
4. WHEN the Client receives the Snapshot and Updates, THE Client SHALL reconstruct the Shared_Document by applying Updates to the Snapshot
5. WHEN reconstruction is complete, THE Editor SHALL render the reconstructed document state

### Requirement 9: Concurrent User Support

**User Story:** As a team, we want 10-20 users to edit simultaneously, so that we can collaborate on documents in real-time.

#### Acceptance Criteria

1. THE WebSocket_Server SHALL support at least 20 concurrent WebSocket connections per document
2. WHEN 20 Clients are connected to a document, THE WebSocket_Server SHALL broadcast Updates to all Clients within 200ms
3. THE Shared_Document SHALL handle concurrent edits from 20 Clients without data corruption
4. WHEN multiple Clients edit the same paragraph simultaneously, THE Shared_Document SHALL merge all edits using Yjs conflict resolution
5. THE WebSocket_Server SHALL maintain connection state for each Client including connection timestamp and last activity timestamp

### Requirement 10: Update Message Format

**User Story:** As a developer, I want a consistent message format, so that Client and Server can communicate reliably.

#### Acceptance Criteria

1. THE Client SHALL send Update messages in JSON format with fields: type, docId, and payload
2. THE payload field SHALL contain the Yjs binary Update encoded as base64 string
3. WHEN the WebSocket_Server receives a message, THE WebSocket_Server SHALL validate the presence of required fields type, docId, and payload
4. IF a message is missing required fields, THEN THE WebSocket_Server SHALL send an error response to the Client and discard the message
5. THE WebSocket_Server SHALL broadcast Update messages to Clients using the same JSON format

### Requirement 11: ProseMirror Schema Definition

**User Story:** As a developer, I want a well-defined document schema, so that the Editor can validate and render content correctly.

#### Acceptance Criteria

1. THE Editor SHALL define a ProseMirror schema with doc as the root Node type
2. THE Editor SHALL define Node types: paragraph, heading (with level attribute 1-3), ordered_list, unordered_list, list_item, table, table_row, table_cell, image (with src attribute), embed (with url attribute), and mention (with userId and displayName attributes)
3. THE Editor SHALL enforce schema constraints preventing invalid Node nesting
4. WHEN the Editor receives content violating the schema, THE Editor SHALL reject the content and log a validation error
5. THE Editor SHALL serialize the schema to JSON format for transmission to the Shared_Document

### Requirement 12: Parser and Pretty Printer for Document Serialization

**User Story:** As a developer, I want to serialize and deserialize documents reliably, so that persistence and transmission work correctly.

#### Acceptance Criteria

1. WHEN a ProseMirror document is provided, THE Parser SHALL serialize it to JSON format conforming to the ProseMirror schema
2. WHEN a JSON document is provided, THE Parser SHALL deserialize it into a valid ProseMirror document object
3. IF the JSON document violates the schema, THEN THE Parser SHALL return a descriptive error indicating the validation failure
4. THE Pretty_Printer SHALL format ProseMirror document objects into valid JSON with consistent indentation
5. FOR ALL valid ProseMirror documents, serializing then deserializing then serializing SHALL produce equivalent JSON output (round-trip property)

### Requirement 13: Error Handling and Recovery

**User Story:** As a user, I want the system to handle errors gracefully, so that I don't lose my work when problems occur.

#### Acceptance Criteria

1. IF the WebSocket_Server encounters an error processing an Update, THEN THE WebSocket_Server SHALL log the error and send an error message to the originating Client
2. IF the Document_Store is unavailable, THEN THE WebSocket_Server SHALL queue Updates in memory and retry persistence every 5 seconds
3. WHEN the Document_Store becomes available after being unavailable, THE WebSocket_Server SHALL persist all queued Updates in order
4. IF a Client receives an invalid Update, THEN THE Client SHALL discard the Update and log a warning without crashing the Editor
5. WHEN the Editor encounters a rendering error, THE Editor SHALL display an error message to the user and preserve the document state

### Requirement 14: Snapshot Generation Strategy

**User Story:** As a system administrator, I want efficient snapshot management, so that document loading remains fast as documents grow.

#### Acceptance Criteria

1. THE WebSocket_Server SHALL generate a new Snapshot when 100 Updates have accumulated since the last Snapshot
2. THE WebSocket_Server SHALL generate a new Snapshot when 5 minutes have elapsed since the last Snapshot, if any Updates exist
3. WHEN generating a Snapshot, THE WebSocket_Server SHALL serialize the current Shared_Document state to JSON format
4. WHEN a Snapshot is successfully stored, THE WebSocket_Server SHALL delete all Updates with version numbers less than or equal to the Snapshot version
5. THE Document_Store SHALL maintain at most one Snapshot per document, replacing the previous Snapshot when a new one is created

### Requirement 15: REST API for Document Operations

**User Story:** As a developer, I want REST endpoints for document management, so that I can integrate the editor with other systems.

#### Acceptance Criteria

1. THE WebSocket_Server SHALL provide endpoint POST /documents that creates a new document and returns the document identifier
2. THE WebSocket_Server SHALL provide endpoint GET /documents/{id} that returns document metadata and the latest Snapshot
3. THE WebSocket_Server SHALL provide endpoint GET /documents that returns a list of all document metadata
4. THE WebSocket_Server SHALL provide endpoint GET /users/search?q={query} that returns users matching the query string
5. WHEN a REST endpoint receives an invalid request, THE WebSocket_Server SHALL return an HTTP 400 error with a descriptive error message

## Notes

This requirements document focuses on the core MVP functionality for real-time collaborative editing. Future enhancements may include cursor presence, user avatars, document permissions, version history UI, and commenting features.
