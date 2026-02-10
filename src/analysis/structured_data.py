"""
Structured Data Collection

Queries free/open data sources for structured intelligence data.
Returns timeseries and structured results from:
- AIS ship tracking (MarineTraffic free API / fallback to web)
- ADS-B flight tracking (OpenSky Network)
- Commodity/trade data (UN Comtrade, World Bank)
- Conflict events (ACLED)
- Satellite imagery indices (Sentinel Hub)

Architecture: Each source has a fetcher that returns normalized results.
If API unavailable, returns instructions for Claude to search manually.
"""

import json
import time
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class DataResult:
    source: str
    query: str
    n_records: int
    data: List[Dict]
    metadata: Dict[str, Any] = field(default_factory=dict)
    fallback_used: bool = False


class StructuredDataCollector:
    """Query structured data sources for intelligence."""
    
    # Available sources and their capabilities
    SOURCES = {
        "opensky_flights": {
            "name": "OpenSky Network (ADS-B)",
            "type": "flight_tracking",
            "api": "https://opensky-network.org/api",
            "free": True,
        },
        "ais_ship_tracking": {
            "name": "AIS Ship Tracking",
            "type": "maritime",
            "api": None,  # No free API — returns search instructions
            "free": False,
        },
        "world_bank": {
            "name": "World Bank Open Data",
            "type": "economic",
            "api": "https://api.worldbank.org/v2",
            "free": True,
        },
        "acled_conflict": {
            "name": "ACLED Conflict Data",
            "type": "conflict_events",
            "api": "https://api.acleddata.com/acled/read",
            "free": True,  # With registration
        },
        "un_comtrade": {
            "name": "UN Comtrade Trade Data",
            "type": "trade",
            "api": "https://comtradeapi.un.org/public/v1/preview",
            "free": True,
        },
    }
    
    def __init__(self):
        self.timeout = 10
    
    def query(self, source: str, params: Dict[str, Any]) -> DataResult:
        """Query a structured data source"""
        if source not in self.SOURCES:
            return DataResult(
                source=source, query=str(params), n_records=0,
                data=[], metadata={"error": f"Unknown source. Available: {list(self.SOURCES.keys())}"}
            )
        
        source_info = self.SOURCES[source]
        
        # Dispatch to source-specific fetcher
        fetchers = {
            "opensky_flights": self._fetch_opensky,
            "world_bank": self._fetch_world_bank,
            "un_comtrade": self._fetch_comtrade,
        }
        
        fetcher = fetchers.get(source)
        if fetcher:
            try:
                return fetcher(params)
            except Exception as e:
                logger.warning(f"Structured data fetch failed for {source}: {e}")
                return self._fallback_instructions(source, params, str(e))
        else:
            return self._fallback_instructions(source, params, "No API available")
    
    def _fetch_opensky(self, params: Dict) -> DataResult:
        """Fetch flight data from OpenSky Network"""
        region = params.get("region", "")
        
        # Bounding boxes for known regions
        bbox = {
            "taiwan_strait": {"lamin": 22.0, "lamax": 26.0, "lomin": 117.0, "lomax": 122.0},
            "black_sea": {"lamin": 41.0, "lamax": 47.0, "lomin": 27.0, "lomax": 42.0},
            "baltic_sea": {"lamin": 53.0, "lamax": 66.0, "lomin": 10.0, "lomax": 30.0},
            "south_china_sea": {"lamin": 5.0, "lamax": 22.0, "lomin": 105.0, "lomax": 120.0},
            "arctic": {"lamin": 66.0, "lamax": 90.0, "lomin": -180.0, "lomax": 180.0},
        }
        
        region_key = region.lower().replace(" ", "_").replace("-", "_")
        box = bbox.get(region_key)
        
        if not box:
            return DataResult(
                source="opensky_flights", query=region, n_records=0, data=[],
                metadata={"available_regions": list(bbox.keys()), "note": "Custom bbox: pass lamin,lamax,lomin,lomax in params"}
            )
        
        # Override with custom bbox if provided
        for k in ["lamin", "lamax", "lomin", "lomax"]:
            if k in params:
                box[k] = float(params[k])
        
        url = f"https://opensky-network.org/api/states/all?lamin={box['lamin']}&lomin={box['lomin']}&lamax={box['lamax']}&lomax={box['lomax']}"
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PLTM/1.0"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read())
            
            states = data.get("states", [])
            flights = []
            for s in states[:50]:  # Cap results
                flights.append({
                    "icao24": s[0],
                    "callsign": (s[1] or "").strip(),
                    "origin_country": s[2],
                    "lat": s[6],
                    "lon": s[5],
                    "altitude_m": s[7],
                    "velocity_ms": s[9],
                    "on_ground": s[8],
                })
            
            return DataResult(
                source="opensky_flights", query=region,
                n_records=len(flights), data=flights,
                metadata={"total_in_region": len(states), "timestamp": data.get("time")}
            )
        except Exception as e:
            return self._fallback_instructions("opensky_flights", params, str(e))
    
    def _fetch_world_bank(self, params: Dict) -> DataResult:
        """Fetch economic indicators from World Bank"""
        indicator = params.get("indicator", "NY.GDP.MKTP.CD")  # GDP default
        country = params.get("country", "all")
        date_range = params.get("date_range", "2020:2025")
        
        url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?date={date_range}&format=json&per_page=50"
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PLTM/1.0"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = json.loads(resp.read())
            
            if not isinstance(raw, list) or len(raw) < 2:
                return DataResult(source="world_bank", query=indicator, n_records=0, data=[],
                                metadata={"error": "No data returned"})
            
            records = []
            for entry in raw[1][:50]:
                if entry.get("value") is not None:
                    records.append({
                        "country": entry.get("country", {}).get("value", ""),
                        "year": entry.get("date"),
                        "value": entry.get("value"),
                        "indicator": entry.get("indicator", {}).get("value", ""),
                    })
            
            return DataResult(
                source="world_bank", query=f"{indicator}/{country}",
                n_records=len(records), data=records,
                metadata={"indicator_id": indicator, "date_range": date_range}
            )
        except Exception as e:
            return self._fallback_instructions("world_bank", params, str(e))
    
    def _fetch_comtrade(self, params: Dict) -> DataResult:
        """Fetch trade data from UN Comtrade"""
        reporter = params.get("reporter", "156")  # China default
        partner = params.get("partner", "0")  # World
        commodity = params.get("commodity", "TOTAL")
        year = params.get("year", "2024")
        flow = params.get("flow", "M")  # M=import, X=export
        
        url = (f"https://comtradeapi.un.org/public/v1/preview/C/A/HS?"
               f"reporterCode={reporter}&partnerCode={partner}"
               f"&cmdCode={commodity}&flowCode={flow}&period={year}")
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PLTM/1.0"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = json.loads(resp.read())
            
            records = []
            for entry in raw.get("data", [])[:30]:
                records.append({
                    "reporter": entry.get("reporterDesc", ""),
                    "partner": entry.get("partnerDesc", ""),
                    "commodity": entry.get("cmdDesc", ""),
                    "flow": entry.get("flowDesc", ""),
                    "value_usd": entry.get("primaryValue"),
                    "year": entry.get("period"),
                })
            
            return DataResult(
                source="un_comtrade", query=f"{reporter}->{partner}/{commodity}",
                n_records=len(records), data=records,
                metadata={"year": year, "flow": flow}
            )
        except Exception as e:
            return self._fallback_instructions("un_comtrade", params, str(e))
    
    def _fallback_instructions(self, source: str, params: Dict, error: str) -> DataResult:
        """Return manual search instructions when API fails"""
        source_info = self.SOURCES.get(source, {})
        
        search_suggestions = {
            "ais_ship_tracking": "Search: MarineTraffic.com or VesselFinder.com for region '{region}'. Look for military vessel movements, unusual patterns.",
            "opensky_flights": "Search: flightradar24.com or OpenSky Explorer for region '{region}'. Look for military aircraft, unusual flight patterns.",
            "acled_conflict": "Search: acleddata.com/dashboard for conflict events. Filter by country/region.",
            "world_bank": "Search: data.worldbank.org for indicator '{indicator}'. Compare across countries.",
            "un_comtrade": "Search: comtradeplus.un.org for trade flows. Filter by commodity and country.",
        }
        
        suggestion = search_suggestions.get(source, f"Search for {source} data manually.")
        suggestion = suggestion.format(**{k: v for k, v in params.items() if isinstance(v, str)})
        
        return DataResult(
            source=source, query=str(params), n_records=0, data=[],
            fallback_used=True,
            metadata={
                "api_error": error[:100],
                "manual_search": suggestion,
                "source_name": source_info.get("name", source),
            }
        )
    
    def list_sources(self) -> List[Dict]:
        """List available data sources"""
        return [
            {"id": k, "name": v["name"], "type": v["type"], "free": v["free"]}
            for k, v in self.SOURCES.items()
        ]
    
    def to_compact(self, result: DataResult) -> Dict:
        """Token-efficient serialization"""
        out = {
            "source": result.source,
            "query": result.query,
            "n": result.n_records,
        }
        if result.data:
            out["data"] = result.data
        if result.fallback_used:
            out["fallback"] = True
        if result.metadata:
            out["meta"] = result.metadata
        return out
