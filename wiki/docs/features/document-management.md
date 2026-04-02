---
sidebar_position: 6
title: Document Management
---

# Document Management

Upload, store, and retrieve permit-related documents via Amazon S3.

## Supported File Types

| Type | Extensions |
|------|-----------|
| PDF | `.pdf` |
| Images | `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic` |
| Documents | `.docx` |
| CAD Plans | `.dwg` |

**Maximum file size:** 25 MB per file.

## Upload Flow

1. User drags files onto the upload zone (or clicks to browse)
2. Files are previewed with thumbnails (images) or type icons (PDF, DOCX)
3. User clicks "Upload" to begin
4. Files are uploaded via `POST /api/v1/documents/upload/{project_id}` (multipart form)
5. Backend validates file type and size, then uploads to S3
6. Document metadata (filename, type, size, S3 key) is stored in the database

## Download

Documents are downloaded via presigned S3 URLs:
1. Request: `GET /api/v1/documents/{document_id}/download`
2. Backend generates a time-limited presigned URL
3. Client redirects to the presigned URL for download

This prevents exposing S3 credentials to the browser.

## Document Types

| Type | Description |
|------|-------------|
| `permit_application` | Permit application form |
| `architectural_plan` | Architectural drawings |
| `structural_plan` | Structural engineering plans |
| `survey` | Land survey |
| `soils_report` | Geotechnical/soils report |
| `photo` | Site photos |
| `clearance_letter` | Department clearance letters |
| `inspection_report` | Inspection results |
| `other` | Other documents |

## Dashboard UI

The DocumentUpload component on the project detail page features:
- Drag-and-drop zone with active state styling
- File preview thumbnails before upload
- Per-file progress bars during upload
- Success checkmarks on completion
- Remove button for pending files
