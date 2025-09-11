"""
Real Wave Solar API Connector for Squidgy Backend
Provides solar insights and data layers from Google Solar API via Real Wave
"""
import os
import httpx
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class SolarApiMode(Enum):
    FULL = "full"
    SUMMARY = "summary"
    SOLAR_RESULTS = "solarResults"

@dataclass
class SolarInsightsRequest:
    address: str
    mode: SolarApiMode = SolarApiMode.FULL
    monthly_electric_bill: Optional[float] = None
    monthly_electric_usage_kwh: Optional[float] = None
    cash_purchase_enabled: bool = True
    financed_purchase_enabled: bool = True
    energy_price_per_kwh: float = 0.17
    installation_price_per_watt: float = 2.0
    dealer_fee_percent: float = 0.15
    solar_incentive_percent: float = 0.30
    financing_apr: float = 0.05
    financing_term_months: int = 240
    installation_lifespan_years: int = 20
    yearly_electric_cost_increase_percent: float = 0.04
    max_roof_segments: int = 4
    typical_panel_count: int = 40
    broker_fee: float = 0.0
    demo: bool = False

@dataclass
class SolarDataLayersRequest:
    address: str
    render_panels: bool = True
    file_format: str = "jpeg"
    demo: bool = False

class SolarApiConnector:
    """Connector for Real Wave Solar API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('SOLAR_API_KEY')
        if not self.api_key:
            raise ValueError("Solar API key not found. Set SOLAR_API_KEY environment variable.")
        
        self.base_url = "https://api.realwave.com"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self._cache = {}  # Simple in-memory cache
        self.cache_duration = 1800  # 30 minutes
    
    async def get_building_insights(self, request: SolarInsightsRequest) -> Dict[str, Any]:
        """
        Get building insights from Google Solar API
        
        Args:
            request: SolarInsightsRequest with address and configuration
            
        Returns:
            Dict containing solar insights and financial estimates
        """
        try:
            # Check cache first
            cache_key = f"insights_{request.address}_{request.mode.value}"
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.info(f"🎯 Returning cached solar insights for {request.address}")
                return cached_result
            
            # Build query parameters
            params = {
                "address": request.address,
                "mode": request.mode.value,
                "demo": str(request.demo).lower(),
                "cashPurchaseEnabled": str(request.cash_purchase_enabled).lower(),
                "financedPurchaseEnabled": str(request.financed_purchase_enabled).lower(),
                "energyPricePerKwh": request.energy_price_per_kwh,
                "installationPricePerWatt": request.installation_price_per_watt,
                "dealerFeePercent": request.dealer_fee_percent,
                "solarIncentivePercent": request.solar_incentive_percent,
                "financingApr": request.financing_apr,
                "financingTermMonths": request.financing_term_months,
                "installationLifespanYears": request.installation_lifespan_years,
                "yearlyElectricCostIncreasePercent": request.yearly_electric_cost_increase_percent,
                "maxRoofSegments": request.max_roof_segments,
                "typicalPanelCount": request.typical_panel_count,
                "brokerFee": request.broker_fee
            }
            
            # Add optional parameters
            if request.monthly_electric_bill:
                params["monthlyElectricBill"] = request.monthly_electric_bill
            if request.monthly_electric_usage_kwh:
                params["monthlyElectricUsageKwh"] = request.monthly_electric_usage_kwh
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/googleSolar/insights",
                    headers=self.headers,
                    params=params
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Cache successful result
                    self._cache_result(cache_key, result)
                    
                    logger.info(f"✅ Solar insights retrieved for {request.address}")
                    logger.info(f"   Credits remaining: {result.get('creditsLeft', 'N/A')}")
                    
                    return result
                    
                elif response.status_code == 401:
                    logger.error("❌ Authentication failed. Check your Solar API key.")
                    return {
                        "error": "Authentication failed",
                        "status_code": 401,
                        "message": "Invalid API key"
                    }
                    
                elif response.status_code == 404:
                    logger.warning(f"⚠️ No solar data found for address: {request.address}")
                    return {
                        "error": "Address not found",
                        "status_code": 404,
                        "message": f"No solar data available for {request.address}"
                    }
                    
                else:
                    logger.error(f"❌ Solar API error: {response.status_code}")
                    return {
                        "error": "API Error",
                        "status_code": response.status_code,
                        "message": response.text
                    }
                    
        except httpx.TimeoutException:
            logger.error("⏱️ Solar API request timed out")
            return {
                "error": "Timeout",
                "message": "Request timed out after 30 seconds"
            }
            
        except Exception as e:
            logger.error(f"❌ Unexpected error in solar API: {str(e)}")
            return {
                "error": "Internal Error",
                "message": str(e)
            }
    
    async def get_solar_data_layers(self, request: SolarDataLayersRequest) -> Dict[str, Any]:
        """
        Get solar data layers and panel visualization for an address
        
        Args:
            request: SolarDataLayersRequest with address and rendering options
            
        Returns:
            Dict containing data layer URLs and panel rendering
        """
        try:
            # Check cache
            cache_key = f"layers_{request.address}_{request.render_panels}"
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.info(f"🎯 Returning cached solar layers for {request.address}")
                return cached_result
            
            # Build request body
            body = {
                "address": request.address,
                "renderPanels": request.render_panels,
                "fileFormat": request.file_format,
                "demo": request.demo
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/googleSolar/dataLayers",
                    headers=self.headers,
                    json=body
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Cache successful result
                    self._cache_result(cache_key, result)
                    
                    logger.info(f"✅ Solar data layers retrieved for {request.address}")
                    
                    return result
                    
                else:
                    logger.error(f"❌ Solar data layers error: {response.status_code}")
                    return {
                        "error": "API Error",
                        "status_code": response.status_code,
                        "message": response.text
                    }
                    
        except Exception as e:
            logger.error(f"❌ Error getting solar data layers: {str(e)}")
            return {
                "error": "Internal Error",
                "message": str(e)
            }
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if still valid"""
        cached = self._cache.get(cache_key)
        if cached and (datetime.now().timestamp() - cached['timestamp']) < self.cache_duration:
            return cached['data']
        elif cached:
            del self._cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, data: Dict[str, Any]):
        """Cache result with timestamp"""
        self._cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now().timestamp()
        }
        
        # Cleanup old cache entries
        if len(self._cache) > 100:
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k]['timestamp']
            )
            del self._cache[oldest_key]

# Example usage for agents
async def get_solar_analysis_for_agent(address: str, monthly_bill: float = None) -> Dict[str, Any]:
    """
    Get solar analysis for use by agents
    
    Args:
        address: Property address
        monthly_bill: Current monthly electric bill
        
    Returns:
        Formatted solar analysis for agent response
    """
    connector = SolarApiConnector()
    
    request = SolarInsightsRequest(
        address=address,
        mode=SolarApiMode.SUMMARY,
        monthly_electric_bill=monthly_bill,
        demo=False  # Set to True for testing without using credits
    )
    
    result = await connector.get_building_insights(request)
    
    if "error" in result:
        return {
            "status": "error",
            "message": result.get("message", "Failed to get solar data")
        }
    
    # Extract key insights from summary
    summary = result.get("rwResult", {}).get("summary", {})
    
    return {
        "status": "success",
        "address": address,
        "solar_potential": summary.get("solarPotential", {}),
        "financial_estimates": summary.get("financialEstimates", {}),
        "environmental_impact": summary.get("environmentalImpact", {}),
        "roof_segments": summary.get("roofSegments", []),
        "ideal_configuration": summary.get("idealConfiguration", {}),
        "credits_remaining": result.get("creditsLeft", "N/A")
    }