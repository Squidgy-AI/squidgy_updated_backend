from mcp.server import Server

app = Server("business-tools")

@app.tool("calculate_roi")
async def calculate_roi(investment: float, return_amount: float, time_period_months: int = 12):
    """Calculate return on investment with time period"""
    try:
        roi_percentage = ((return_amount - investment) / investment) * 100
        annualized_roi = (roi_percentage / time_period_months) * 12
        
        return {
            "investment": investment,
            "return_amount": return_amount,
            "time_period_months": time_period_months,
            "roi_percentage": round(roi_percentage, 2),
            "annualized_roi": round(annualized_roi, 2),
            "profit": round(return_amount - investment, 2)
        }
    except Exception as e:
        return {"error": str(e)}

@app.tool("calculate_lead_value")
async def calculate_lead_value(
    conversion_rate: float,
    average_deal_size: float,
    cost_per_lead: float
):
    """Calculate the lifetime value of a lead"""
    try:
        expected_revenue = conversion_rate * average_deal_size
        profit_per_lead = expected_revenue - cost_per_lead
        roi_per_lead = (profit_per_lead / cost_per_lead) * 100 if cost_per_lead > 0 else 0
        
        return {
            "conversion_rate": conversion_rate,
            "average_deal_size": average_deal_size,
            "cost_per_lead": cost_per_lead,
            "expected_revenue": round(expected_revenue, 2),
            "profit_per_lead": round(profit_per_lead, 2),
            "roi_per_lead": round(roi_per_lead, 2)
        }
    except Exception as e:
        return {"error": str(e)}

@app.tool("analyze_campaign_performance")
async def analyze_campaign_performance(
    impressions: int,
    clicks: int,
    conversions: int,
    cost: float,
    revenue: float = 0
):
    """Analyze marketing campaign performance metrics"""
    try:
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
        cost_per_click = (cost / clicks) if clicks > 0 else 0
        cost_per_conversion = (cost / conversions) if conversions > 0 else 0
        
        roi = ((revenue - cost) / cost * 100) if cost > 0 else 0
        
        return {
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "cost": cost,
            "revenue": revenue,
            "metrics": {
                "ctr": round(ctr, 2),
                "conversion_rate": round(conversion_rate, 2),
                "cost_per_click": round(cost_per_click, 2),
                "cost_per_conversion": round(cost_per_conversion, 2),
                "roi": round(roi, 2)
            }
        }
    except Exception as e:
        return {"error": str(e)}

@app.tool("generate_business_report")
async def generate_business_report(metrics: dict, period: str = "monthly"):
    """Generate a business performance report"""
    try:
        report = {
            "period": period,
            "generated_at": "2024-01-01",  # You'd use datetime.now() in real implementation
            "summary": {
                "total_revenue": metrics.get("revenue", 0),
                "total_cost": metrics.get("cost", 0),
                "profit": metrics.get("revenue", 0) - metrics.get("cost", 0),
                "leads_generated": metrics.get("leads", 0),
                "conversions": metrics.get("conversions", 0)
            },
            "recommendations": []
        }
        
        # Add recommendations based on metrics
        if report["summary"]["profit"] < 0:
            report["recommendations"].append("Consider reducing costs or improving conversion rates")
        
        if metrics.get("conversion_rate", 0) < 5:
            report["recommendations"].append("Focus on improving lead quality and nurturing")
            
        return report
    except Exception as e:
        return {"error": str(e)}