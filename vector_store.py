# Modified vector_store.py for Redis Cloud
import os
import pandas as pd
import json
import numpy as np
from typing import List, Dict, Optional
import redis
import pickle

class VectorStore:
    def __init__(self):
        # Connect to Redis Cloud
        self.redis = self._get_redis_connection()
        self.collection_name = "conversation_templates"
        
    def _get_redis_connection(self):
        """Create a Redis connection from Heroku REDISCLOUD_URL"""
        redis_url = os.environ.get('REDISCLOUD_URL')
        if not redis_url:
            raise ValueError("REDISCLOUD_URL environment variable not set")
            
        return redis.from_url(redis_url)
    
    def _get_squidgy_response(self, row: pd.Series) -> str:
        """Get Squidgy's response from either column format"""
        if 'As Squidgy' in row and pd.notna(row['As Squidgy']):
            return row['As Squidgy']
        elif 'As Squidgy (Template for Reference)' in row and pd.notna(row['As Squidgy (Template for Reference)']):
            return row['As Squidgy (Template for Reference)']
        return ''
    
    def load_excel_templates(self, excel_content: bytes) -> bool:
        """Load templates from Excel file content"""
        try:
            from io import BytesIO
            df = pd.read_excel(BytesIO(excel_content))
            
            # Verify required columns
            if 'Role' not in df.columns:
                raise ValueError("Excel file must contain 'Role' column")
            
            # Check for either response column
            if 'Clients probable response' not in df.columns:
                raise ValueError("Excel file must contain 'Clients probable response' column")
            
            # Check for either Squidgy column format
            if not ('As Squidgy' in df.columns or 'As Squidgy (Template for Reference)' in df.columns):
                raise ValueError("Excel file must contain either 'As Squidgy' or 'As Squidgy (Template for Reference)' column")
            
            # Clear existing data
            for key in self.redis.scan_iter(f"{self.collection_name}:*"):
                self.redis.delete(key)
            
            # Store role indices for quick lookup
            role_indices = {}
            
            for idx, row in df.iterrows():
                role = row['Role']
                client_response = row.get('Clients probable response', '')
                squidgy_response = self._get_squidgy_response(row)
                
                # Create text representation
                text = f"Role: {role}\n"
                if pd.notna(client_response):
                    text += f"Client Response: {client_response}\n"
                if squidgy_response:
                    text += f"Template: {squidgy_response}\n"
                
                # Store template data
                template_key = f"{self.collection_name}:{idx}"
                template_data = {
                    "role": role,
                    "client_response": client_response,
                    "template": squidgy_response,
                    "text": text
                }
                
                self.redis.set(template_key, json.dumps(template_data))
                
                # Track templates by role
                if role not in role_indices:
                    role_indices[role] = []
                role_indices[role].append(idx)
            
            # Store role indices
            for role, indices in role_indices.items():
                self.redis.set(f"{self.collection_name}:role:{role}", json.dumps(indices))
            
            print(f"Successfully loaded {len(df)} templates")
            return True
            
        except Exception as e:
            print(f"Error loading templates: {str(e)}")
            return False

    def get_role_templates(self, role: str, n_results: int = 3) -> List[Dict]:
        """Get templates for a specific role"""
        # Get indices for this role
        indices_key = f"{self.collection_name}:role:{role}"
        indices_json = self.redis.get(indices_key)
        
        if not indices_json:
            return []
            
        indices = json.loads(indices_json)
        results = []
        
        # Get up to n_results templates
        for idx in indices[:n_results]:
            template_key = f"{self.collection_name}:{idx}"
            template_json = self.redis.get(template_key)
            
            if template_json:
                template_data = json.loads(template_json)
                template_data["score"] = 1.0  # Placeholder score
                results.append(template_data)
        
        return results

    def get_all_templates_for_role(self, role: str) -> List[Dict]:
        """Get all templates for a specific role"""
        # Get indices for this role
        indices_key = f"{self.collection_name}:role:{role}"
        indices_json = self.redis.get(indices_key)
        
        if not indices_json:
            return []
            
        indices = json.loads(indices_json)
        results = []
        
        # Get all templates for this role (limit to 100)
        for idx in indices[:100]:
            template_key = f"{self.collection_name}:{idx}"
            template_json = self.redis.get(template_key)
            
            if template_json:
                results.append(json.loads(template_json))
        
        return results

    def find_similar_response(self, client_message: str, n_results: int = 3) -> List[Dict]:
        """Find similar templates based on client message"""
        # In this simplified version, just return some random templates
        # For a production version, you'd implement more sophisticated matching
        
        # Get all role keys
        role_keys = []
        for key in self.redis.scan_iter(f"{self.collection_name}:role:*"):
            role_keys.append(key)
        
        if not role_keys:
            return []
            
        # Get a random role's templates
        random_role_key = role_keys[0]
        indices_json = self.redis.get(random_role_key)
        
        if not indices_json:
            return []
            
        indices = json.loads(indices_json)
        results = []
        
        # Get up to n_results templates
        for idx in indices[:n_results]:
            template_key = f"{self.collection_name}:{idx}"
            template_json = self.redis.get(template_key)
            
            if template_json:
                template_data = json.loads(template_json)
                template_data["score"] = 0.5  # Placeholder score
                results.append(template_data)
            
        return results
    
    def has_templates(self) -> bool:
        """Check if Redis already has templates loaded"""
        # Check if there are any keys matching our collection pattern
        return bool(list(self.redis.scan_iter(f"{self.collection_name}:*", count=1)))


# # vector_store.py
# import pandas as pd
# from sentence_transformers import SentenceTransformer
# from qdrant_client import QdrantClient
# from qdrant_client.http import models
# from typing import List, Dict, Optional

# class VectorStore:
#     def __init__(self):
#         # Initialize Qdrant in memory
#         self.client = QdrantClient(":memory:")
#         self.model = SentenceTransformer('all-MiniLM-L6-v2')
#         self.collection_name = "conversation_templates"
        
#         # Create collection
#         self.client.recreate_collection(
#             collection_name=self.collection_name,
#             vectors_config=models.VectorParams(
#                 size=384,  # Vector size for 'all-MiniLM-L6-v2'
#                 distance=models.Distance.COSINE
#             )
#         )
    
#     def _get_squidgy_response(self, row: pd.Series) -> str:
#         """Get Squidgy's response from either column format"""
#         if 'As Squidgy' in row and pd.notna(row['As Squidgy']):
#             return row['As Squidgy']
#         elif 'As Squidgy (Template for Reference)' in row and pd.notna(row['As Squidgy (Template for Reference)']):
#             return row['As Squidgy (Template for Reference)']
#         return ''
    
#     def load_excel_templates(self, excel_content: bytes) -> bool:
#         """Load templates from Excel file content"""
#         try:
#             from io import BytesIO
#             df = pd.read_excel(BytesIO(excel_content))
            
#             # Verify required columns
#             if 'Role' not in df.columns:
#                 raise ValueError("Excel file must contain 'Role' column")
            
#             # Check for either response column
#             if 'Clients probable response' not in df.columns:
#                 raise ValueError("Excel file must contain 'Clients probable response' column")
            
#             # Check for either Squidgy column format
#             if not ('As Squidgy' in df.columns or 'As Squidgy (Template for Reference)' in df.columns):
#                 raise ValueError("Excel file must contain either 'As Squidgy' or 'As Squidgy (Template for Reference)' column")
            
#             for idx, row in df.iterrows():
#                 # Get Squidgy's response using helper method
#                 squidgy_response = self._get_squidgy_response(row)
                
#                 # Create text representation
#                 text = f"Role: {row['Role']}\n"
#                 if pd.notna(row['Clients probable response']):
#                     text += f"Client Response: {row['Clients probable response']}\n"
#                 if squidgy_response:
#                     text += f"Template: {squidgy_response}\n"
                
#                 # Create embedding
#                 embedding = self.model.encode(text)
                
#                 # Store in Qdrant
#                 self.client.upsert(
#                     collection_name=self.collection_name,
#                     points=[
#                         models.PointStruct(
#                             id=idx,
#                             vector=embedding.tolist(),
#                             payload={
#                                 "role": row['Role'],
#                                 "client_response": row.get('Clients probable response', ''),
#                                 "template": squidgy_response,
#                                 "text": text
#                             }
#                         )
#                     ]
#                 )
#             print(f"Successfully loaded {len(df)} templates")
#             return True
            
#         except Exception as e:
#             print(f"Error loading templates: {str(e)}")
#             return False

#     def get_role_templates(self, role: str, n_results: int = 3) -> List[Dict]:
#         """Get templates for a specific role"""
#         query_text = f"Role: {role}"
#         query_vector = self.model.encode(query_text)
        
#         results = self.client.search(
#             collection_name=self.collection_name,
#             query_vector=query_vector,
#             limit=n_results
#         )
        
#         return [
#             {
#                 "role": hit.payload["role"],
#                 "client_response": hit.payload["client_response"],
#                 "template": hit.payload["template"],
#                 "score": hit.score
#             }
#             for hit in results
#         ]

#     def get_all_templates_for_role(self, role: str) -> List[Dict]:
#         """Get all templates for a specific role"""
#         # Using search instead of scroll for simpler handling
#         results = self.client.search(
#             collection_name=self.collection_name,
#             query_vector=self.model.encode(f"Role: {role}"),
#             query_filter=models.Filter(
#                 must=[
#                     models.FieldCondition(
#                         key="role",
#                         match=models.MatchValue(value=role)
#                     )
#                 ]
#             ),
#             limit=100  # Increased limit to get all templates
#         )
        
#         return [
#             {
#                 "role": hit.payload["role"],
#                 "client_response": hit.payload["client_response"],
#                 "template": hit.payload["template"]
#             }
#             for hit in results
#         ]

#     def find_similar_response(self, client_message: str, n_results: int = 3) -> List[Dict]:
#         """Find similar templates based on client message"""
#         query_vector = self.model.encode(client_message)
        
#         results = self.client.search(
#             collection_name=self.collection_name,
#             query_vector=query_vector,
#             limit=n_results
#         )
        
#         return [
#             {
#                 "role": hit.payload["role"],
#                 "client_response": hit.payload["client_response"],
#                 "template": hit.payload["template"],
#                 "score": hit.score
#             }
#             for hit in results
#         ]