# DoseWise API Contract

This document defines the agreement between the DoseWise frontend and backend.

## Medicine Object
The medicine object is the standard representation used between frontend and backend.

```json
{
  "brand": "Dolo 650",
  "salts": ["Paracetamol"],
  "strength": "650 mg",
  "slots": ["morning", "night"],
  "food": "after",
  "durationDays": 5,
  "photoUrl": "/pills/dolo.jpg",
  "confidence": 0.92
}   
## POST /families

## POST /parents

## POST /scans/upload-url

## GET /scans/{id}

## POST /meds/confirm

## GET /parents/{id}/today

## POST /doses/{id}/taken

## GET /parents/{id}/dashboard

## GET /parents/{id}/voice?slot={slot}

## POST /parents/{id}/visit-card