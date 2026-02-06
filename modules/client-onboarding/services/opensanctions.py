"""
OpenSanctions API Integration
Provides sanctions, PEP, and adverse media screening

Supports both live API mode (with API key) and demo mode (without API key)
for PoC demonstrations.
"""

import os
import requests
import logging
import hashlib
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# OpenSanctions API configuration
OPENSANCTIONS_API_URL = "https://api.opensanctions.org"
OPENSANCTIONS_API_KEY = os.environ.get('OPENSANCTIONS_API_KEY', '')

# Default dataset for comprehensive screening
DEFAULT_DATASET = "default"  # Includes sanctions, PEPs, and crime

# Demo mode - activated when no API key is provided
DEMO_MODE = not OPENSANCTIONS_API_KEY

# Mock data for demo mode - provides realistic screening results
MOCK_SANCTIONS_KEYWORDS = ['putin', 'kim', 'assad', 'lukashenko', 'maduro', 'khamenei']
MOCK_PEP_KEYWORDS = ['minister', 'senator', 'governor', 'ambassador', 'president', 'chancellor']
MOCK_ADVERSE_KEYWORDS = ['fraud', 'criminal', 'wanted', 'fugitive']

# Specific mock entities for demo purposes
MOCK_ENTITIES = {
    # Sanctions hits
    'vladimir putin': {
        'type': 'sanctions',
        'score': 0.98,
        'datasets': ['eu_fsf', 'us_ofac_sdn', 'gb_hmt_sanctions'],
        'caption': 'Vladimir Vladimirovich Putin',
        'topics': ['sanction'],
        'description': 'President of the Russian Federation. Designated under multiple sanctions programs.'
    },
    'kim jong un': {
        'type': 'sanctions',
        'score': 0.95,
        'datasets': ['us_ofac_sdn', 'un_sc_sanctions'],
        'caption': 'Kim Jong Un',
        'topics': ['sanction'],
        'description': 'Supreme Leader of North Korea. Designated under UN and US sanctions.'
    },
    # PEP examples
    'boris johnson': {
        'type': 'pep',
        'score': 0.92,
        'datasets': ['gb_coh_psc', 'everypolitician'],
        'caption': 'Boris Johnson',
        'topics': ['role.pep'],
        'description': 'Former Prime Minister of the United Kingdom (2019-2022).'
    },
    'david cameron': {
        'type': 'pep',
        'score': 0.88,
        'datasets': ['gb_coh_psc', 'everypolitician'],
        'caption': 'David Cameron',
        'topics': ['role.pep'],
        'description': 'Former Prime Minister of the United Kingdom. Current Foreign Secretary.'
    },
    # Adverse media example
    'sam bankman-fried': {
        'type': 'adverse',
        'score': 0.94,
        'datasets': ['icij_offshoreleaks', 'us_doj_wanted'],
        'caption': 'Sam Bankman-Fried',
        'topics': ['crime.fin'],
        'description': 'Former CEO of FTX cryptocurrency exchange. Convicted of fraud.'
    }
}


class OpenSanctionsClient:
    """Client for OpenSanctions API"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or OPENSANCTIONS_API_KEY
        self.base_url = OPENSANCTIONS_API_URL
        self.demo_mode = not self.api_key
        self.session = requests.Session()
        if self.api_key:
            self.session.headers['Authorization'] = f'ApiKey {self.api_key}'
        self.session.headers['Content-Type'] = 'application/json'

        if self.demo_mode:
            logger.info("OpenSanctions running in DEMO MODE - using mock data")

    def _generate_demo_result(self, name: str, entity_type: str = 'person') -> Dict[str, Any]:
        """Generate demo/mock screening result for demonstration purposes"""
        name_lower = name.lower().strip()

        # Check for exact matches in mock entities
        if name_lower in MOCK_ENTITIES:
            mock = MOCK_ENTITIES[name_lower]
            match_data = {
                "id": f"demo-{hashlib.md5(name_lower.encode()).hexdigest()[:8]}",
                "name": mock['caption'],
                "score": mock['score'],
                "match": True,
                "schema": "Person" if entity_type == 'person' else "Company",
                "datasets": mock['datasets'],
                "type": mock['type'],
                "properties": {
                    "topics": mock.get('topics', []),
                    "description": [mock.get('description', '')]
                }
            }

            has_sanctions = mock['type'] == 'sanctions'
            has_pep = mock['type'] == 'pep'
            has_adverse = mock['type'] == 'adverse'

            return {
                "status": "success",
                "demo_mode": True,
                "query_id": "q1",
                "total_matches": 1,
                "has_sanctions_hit": has_sanctions,
                "has_pep_hit": has_pep,
                "has_adverse_media": has_adverse,
                "risk_level": self._calculate_risk_level(has_sanctions, has_pep, has_adverse, [match_data]),
                "matches": [match_data]
            }

        # Check for keyword matches
        has_sanctions = any(kw in name_lower for kw in MOCK_SANCTIONS_KEYWORDS)
        has_pep = any(kw in name_lower for kw in MOCK_PEP_KEYWORDS)
        has_adverse = any(kw in name_lower for kw in MOCK_ADVERSE_KEYWORDS)

        if has_sanctions or has_pep or has_adverse:
            match_type = 'sanctions' if has_sanctions else ('pep' if has_pep else 'adverse')
            score = 0.75 + (hash(name_lower) % 20) / 100  # Pseudo-random score 0.75-0.95

            match_data = {
                "id": f"demo-{hashlib.md5(name_lower.encode()).hexdigest()[:8]}",
                "name": name.title(),
                "score": round(score, 2),
                "match": score > 0.8,
                "schema": "Person" if entity_type == 'person' else "Company",
                "datasets": ["demo_dataset"],
                "type": match_type,
                "properties": {"topics": [f"role.{match_type}" if match_type == 'pep' else match_type]}
            }

            return {
                "status": "success",
                "demo_mode": True,
                "query_id": "q1",
                "total_matches": 1,
                "has_sanctions_hit": has_sanctions,
                "has_pep_hit": has_pep,
                "has_adverse_media": has_adverse,
                "risk_level": self._calculate_risk_level(has_sanctions, has_pep, has_adverse, [match_data]),
                "matches": [match_data]
            }

        # No matches found - clear result
        return {
            "status": "success",
            "demo_mode": True,
            "query_id": "q1",
            "total_matches": 0,
            "has_sanctions_hit": False,
            "has_pep_hit": False,
            "has_adverse_media": False,
            "risk_level": "clear",
            "matches": []
        }

    def match_person(
        self,
        name: str,
        birth_date: str = None,
        nationality: str = None,
        id_number: str = None,
        dataset: str = DEFAULT_DATASET,
        threshold: float = 0.5,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Match a person against sanctions/PEP lists

        Args:
            name: Full name of the person
            birth_date: Date of birth (YYYY-MM-DD format)
            nationality: Country code (e.g., 'gb', 'us')
            id_number: Passport or ID number
            dataset: Dataset to search (default, sanctions, peps, etc.)
            threshold: Match score threshold (0-1)
            limit: Maximum results to return

        Returns:
            Dict with matches and screening results
        """
        # Use demo mode if no API key
        if self.demo_mode:
            return self._generate_demo_result(name, 'person')

        # Build the entity query
        properties = {
            "name": [name]
        }

        if birth_date:
            properties["birthDate"] = [birth_date]
        if nationality:
            properties["nationality"] = [nationality.lower()]
        if id_number:
            properties["idNumber"] = [id_number]

        query = {
            "queries": {
                "q1": {
                    "schema": "Person",
                    "properties": properties
                }
            }
        }

        try:
            response = self.session.post(
                f"{self.base_url}/match/{dataset}",
                json=query,
                params={"threshold": threshold, "limit": limit},
                timeout=30
            )
            response.raise_for_status()
            return self._parse_match_response(response.json(), "q1")

        except requests.exceptions.RequestException as e:
            logger.error(f"OpenSanctions API error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "matches": []
            }

    def match_company(
        self,
        name: str,
        jurisdiction: str = None,
        registration_number: str = None,
        dataset: str = DEFAULT_DATASET,
        threshold: float = 0.5,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Match a company against sanctions lists

        Args:
            name: Company legal name
            jurisdiction: Country code
            registration_number: Company registration number
            dataset: Dataset to search
            threshold: Match score threshold
            limit: Maximum results

        Returns:
            Dict with matches and screening results
        """
        # Use demo mode if no API key
        if self.demo_mode:
            return self._generate_demo_result(name, 'company')

        properties = {
            "name": [name]
        }

        if jurisdiction:
            properties["jurisdiction"] = [jurisdiction.lower()]
        if registration_number:
            properties["registrationNumber"] = [registration_number]

        query = {
            "queries": {
                "q1": {
                    "schema": "Company",
                    "properties": properties
                }
            }
        }

        try:
            response = self.session.post(
                f"{self.base_url}/match/{dataset}",
                json=query,
                params={"threshold": threshold, "limit": limit},
                timeout=30
            )
            response.raise_for_status()
            return self._parse_match_response(response.json(), "q1")

        except requests.exceptions.RequestException as e:
            logger.error(f"OpenSanctions API error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "matches": []
            }

    def batch_screen(
        self,
        entities: List[Dict],
        dataset: str = DEFAULT_DATASET,
        threshold: float = 0.5
    ) -> Dict[str, Dict]:
        """
        Screen multiple entities in a single API call

        Args:
            entities: List of entity dicts with 'name', 'type' (person/company), and optional fields
            dataset: Dataset to search
            threshold: Match score threshold

        Returns:
            Dict mapping entity names to their screening results
        """
        # Use demo mode if no API key
        if self.demo_mode:
            results = {}
            for entity in entities:
                entity_type = entity.get('type', 'person').lower()
                results[entity['name']] = self._generate_demo_result(entity['name'], entity_type)
            return results

        queries = {}
        for i, entity in enumerate(entities):
            query_id = f"q{i}"
            entity_type = entity.get('type', 'person').lower()

            if entity_type == 'person':
                properties = {"name": [entity['name']]}
                if entity.get('birth_date'):
                    properties["birthDate"] = [entity['birth_date']]
                if entity.get('nationality'):
                    properties["nationality"] = [entity['nationality'].lower()]
                queries[query_id] = {
                    "schema": "Person",
                    "properties": properties
                }
            else:
                properties = {"name": [entity['name']]}
                if entity.get('jurisdiction'):
                    properties["jurisdiction"] = [entity['jurisdiction'].lower()]
                queries[query_id] = {
                    "schema": "Company",
                    "properties": properties
                }

        try:
            response = self.session.post(
                f"{self.base_url}/match/{dataset}",
                json={"queries": queries},
                params={"threshold": threshold},
                timeout=60
            )
            response.raise_for_status()
            data = response.json()

            results = {}
            for i, entity in enumerate(entities):
                query_id = f"q{i}"
                results[entity['name']] = self._parse_match_response(data, query_id)

            return results

        except requests.exceptions.RequestException as e:
            logger.error(f"OpenSanctions batch API error: {e}")
            return {
                entity['name']: {"status": "error", "error": str(e), "matches": []}
                for entity in entities
            }

    def _parse_match_response(self, data: Dict, query_id: str) -> Dict[str, Any]:
        """Parse the API response into a cleaner format"""
        responses = data.get("responses", {})
        query_response = responses.get(query_id, {})
        results = query_response.get("results", [])

        matches = []
        has_sanctions_hit = False
        has_pep_hit = False
        has_adverse_media = False

        for result in results:
            match_data = {
                "id": result.get("id"),
                "name": result.get("caption"),
                "score": result.get("score", 0),
                "match": result.get("match", False),
                "schema": result.get("schema"),
                "datasets": result.get("datasets", []),
                "properties": result.get("properties", {})
            }

            # Determine match type based on datasets
            datasets = result.get("datasets", [])
            topics = result.get("properties", {}).get("topics", [])

            if any(d in datasets for d in ["eu_fsf", "us_ofac_sdn", "un_sc_sanctions", "gb_hmt_sanctions"]):
                has_sanctions_hit = True
                match_data["type"] = "sanctions"
            elif "role.pep" in topics or any("pep" in d.lower() for d in datasets):
                has_pep_hit = True
                match_data["type"] = "pep"
            elif any("crime" in d.lower() or "wanted" in d.lower() for d in datasets):
                has_adverse_media = True
                match_data["type"] = "adverse"
            else:
                match_data["type"] = "other"

            matches.append(match_data)

        return {
            "status": "success",
            "query_id": query_id,
            "total_matches": len(matches),
            "has_sanctions_hit": has_sanctions_hit,
            "has_pep_hit": has_pep_hit,
            "has_adverse_media": has_adverse_media,
            "risk_level": self._calculate_risk_level(has_sanctions_hit, has_pep_hit, has_adverse_media, matches),
            "matches": matches
        }

    def _calculate_risk_level(
        self,
        has_sanctions: bool,
        has_pep: bool,
        has_adverse: bool,
        matches: List[Dict]
    ) -> str:
        """Calculate risk level based on screening results"""
        if has_sanctions:
            return "critical"  # Potential deal-breaker
        if has_pep and any(m.get("score", 0) > 0.8 for m in matches):
            return "high"
        if has_pep or has_adverse:
            return "medium"
        if matches and any(m.get("score", 0) > 0.7 for m in matches):
            return "review"  # Needs manual review
        return "clear"


# Singleton instance
_client = None


def get_client() -> OpenSanctionsClient:
    """Get or create OpenSanctions client instance"""
    global _client
    if _client is None:
        _client = OpenSanctionsClient()
    return _client


def screen_person(name: str, **kwargs) -> Dict[str, Any]:
    """Convenience function to screen a person"""
    return get_client().match_person(name, **kwargs)


def screen_company(name: str, **kwargs) -> Dict[str, Any]:
    """Convenience function to screen a company"""
    return get_client().match_company(name, **kwargs)


def batch_screen(entities: List[Dict], **kwargs) -> Dict[str, Dict]:
    """Convenience function for batch screening"""
    return get_client().batch_screen(entities, **kwargs)
