#!/usr/bin/env python3
"""
🚀 SIMPLIFIED FACEBOOK INTEGRATION SERVER
========================================
Minimal FastAPI server for Facebook integration only
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

# Import our Facebook integration
from facebook_pages_api_working import FacebookPagesRequest, FacebookPagesResponse, get_facebook_pages

# Create FastAPI app
app = FastAPI(title="Facebook Integration API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Facebook Integration API is running!", "status": "healthy"}

@app.post("/api/facebook/get-pages", response_model=FacebookPagesResponse)
async def get_facebook_pages_endpoint(request: FacebookPagesRequest):
    """
    Main Facebook integration endpoint
    Handles 2FA automation, JWT extraction, and Facebook pages retrieval
    """
    return await get_facebook_pages(request)

@app.get("/health")
async def health_check():
    """Health check for monitoring"""
    return {"status": "ok", "service": "facebook-integration"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
