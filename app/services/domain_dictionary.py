"""
Domain Dictionary for Automotive Standards.
Contains terminology and definitions for ASPICE, AUTOSAR, and ISO26262.
"""

from typing import Dict, List, Optional


# ASPICE (Automotive SPICE) Terms
ASPICE_TERMS = {
    "ASPICE": "Automotive SPICE - A process assessment model for automotive software development, derived from ISO/IEC 15504.",
    "SWE.1": "Software Requirements Analysis - Process to establish software requirements.",
    "SWE.2": "Software Architectural Design - Process to establish software architecture.",
    "SWE.3": "Software Detailed Design and Unit Construction - Process to create detailed design and code.",
    "SWE.4": "Software Unit Verification - Process to verify software units.",
    "SWE.5": "Software Integration and Integration Test - Process to integrate software units.",
    "SWE.6": "Software Qualification Test - Process to qualify the integrated software.",
    "SYS.1": "Requirements Elicitation - Process to gather stakeholder requirements.",
    "SYS.2": "System Requirements Analysis - Process to transform stakeholder requirements into system requirements.",
    "SYS.3": "System Architectural Design - Process to establish system architecture.",
    "SYS.4": "System Integration and Integration Test - Process to integrate system elements.",
    "SYS.5": "System Qualification Test - Process to qualify the integrated system.",
    "MAN.3": "Project Management - Process to identify, establish, coordinate and monitor activities.",
    "SUP.8": "Configuration Management - Process to establish and maintain integrity of work products.",
    "SUP.9": "Problem Resolution Management - Process to ensure problems are identified and resolved.",
    "SUP.10": "Change Request Management - Process to ensure change requests are managed.",
    "Capability Level": "A scale from 0-5 measuring process capability (Incomplete to Optimizing).",
    "Base Practice": "An activity that addresses the purpose of a process.",
    "Work Product": "An artifact associated with a process.",
}

# AUTOSAR Terms
AUTOSAR_TERMS = {
    "AUTOSAR": "AUTomotive Open System ARchitecture - A worldwide development partnership of vehicle manufacturers, suppliers and tool developers.",
    "SWC": "Software Component - A piece of application software implementing part of an application.",
    "RTE": "Runtime Environment - The layer providing communication services between SWCs.",
    "BSW": "Basic Software - Standardized software modules providing services to SWCs.",
    "MCAL": "Microcontroller Abstraction Layer - BSW layer providing abstraction of microcontroller peripherals.",
    "ECU": "Electronic Control Unit - An embedded system controlling electrical systems in a vehicle.",
    "VFB": "Virtual Functional Bus - Concept for SWC communication abstraction.",
    "ARXML": "AUTOSAR XML - XML-based file format for AUTOSAR descriptions.",
    "PDU": "Protocol Data Unit - A data unit for network communication.",
    "COM": "Communication - AUTOSAR module handling signal-based communication.",
    "DCM": "Diagnostic Communication Manager - Module handling diagnostic communication.",
    "DEM": "Diagnostic Event Manager - Module handling diagnostic event storage.",
    "NVM": "Non-Volatile Memory Manager - Module handling persistent data storage.",
    "OS": "Operating System - AUTOSAR OS module providing real-time OS services.",
    "Adaptive AUTOSAR": "AUTOSAR platform for high-performance computing ECUs using POSIX-based OS.",
    "Classic AUTOSAR": "AUTOSAR platform for deeply embedded ECUs with static configuration.",
    "Manifest": "Deployment information for Adaptive AUTOSAR applications.",
    "ara::com": "Adaptive AUTOSAR communication middleware API.",
}

# ISO 26262 (Functional Safety) Terms
ISO26262_TERMS = {
    "ISO 26262": "International standard for functional safety of road vehicles containing E/E systems.",
    "ASIL": "Automotive Safety Integrity Level - Risk classification from A (lowest) to D (highest).",
    "ASIL A": "Lowest automotive safety integrity level.",
    "ASIL B": "Second lowest automotive safety integrity level.",
    "ASIL C": "Second highest automotive safety integrity level.",
    "ASIL D": "Highest automotive safety integrity level, most stringent requirements.",
    "QM": "Quality Management - Non-safety-related, standard quality processes apply.",
    "HARA": "Hazard Analysis and Risk Assessment - Process to identify hazards and assess risks.",
    "FSC": "Functional Safety Concept - High-level safety requirements allocation.",
    "TSC": "Technical Safety Concept - Technical safety requirements derived from FSC.",
    "HSI": "Hardware-Software Interface - Specification of HW/SW interaction.",
    "FMEA": "Failure Mode and Effects Analysis - Analysis technique for potential failure modes.",
    "FTA": "Fault Tree Analysis - Top-down analysis of system failures.",
    "SOTIF": "Safety of the Intended Functionality - ISO 21448, addresses intended function safety.",
    "Functional Safety": "Absence of unreasonable risk due to hazards caused by malfunctioning E/E systems.",
    "Safety Goal": "Top-level safety requirement resulting from HARA.",
    "Safety Mechanism": "Technical solution to detect faults or control failures.",
    "Diagnostic Coverage": "Percentage of dangerous failures detected by safety mechanisms.",
    "PMHF": "Probabilistic Metric for Hardware Failures - Target value for residual risk.",
    "SPFM": "Single Point Fault Metric - Metric for single point fault coverage.",
    "LFM": "Latent Fault Metric - Metric for multi-point fault detection coverage.",
    "DFA": "Dependent Failure Analysis - Analysis of common cause and cascading failures.",
    "V-Model": "Development lifecycle model with verification at each stage.",
}


class DomainDictionary:
    """Domain dictionary for automotive terminology."""
    
    def __init__(self):
        self.dictionaries = {
            "ASPICE": ASPICE_TERMS,
            "AUTOSAR": AUTOSAR_TERMS,
            "ISO26262": ISO26262_TERMS,
        }
        
        # Combined dictionary for full-text search
        self.all_terms = {}
        for domain, terms in self.dictionaries.items():
            for term, definition in terms.items():
                self.all_terms[term] = {
                    "definition": definition,
                    "domain": domain
                }
    
    def lookup(self, term: str) -> Optional[Dict]:
        """Look up a term in the dictionary."""
        # Exact match (case-insensitive)
        term_upper = term.upper()
        for key, value in self.all_terms.items():
            if key.upper() == term_upper:
                return {"term": key, **value}
        
        # Partial match
        matches = []
        for key, value in self.all_terms.items():
            if term_upper in key.upper():
                matches.append({"term": key, **value})
        
        if matches:
            return matches[0] if len(matches) == 1 else {"matches": matches}
        
        return None
    
    def get_domain_terms(self, domain: str) -> Dict[str, str]:
        """Get all terms for a specific domain."""
        domain = domain.upper()
        if domain in self.dictionaries:
            return self.dictionaries[domain]
        return {}
    
    def search(self, query: str) -> List[Dict]:
        """Search for terms containing the query."""
        query_lower = query.lower()
        results = []
        
        for term, info in self.all_terms.items():
            if (query_lower in term.lower() or 
                query_lower in info["definition"].lower()):
                results.append({
                    "term": term,
                    "definition": info["definition"],
                    "domain": info["domain"]
                })
        
        return results
    
    def get_context_for_query(self, query: str) -> str:
        """
        Generate context string with relevant domain terms for a query.
        Useful for augmenting RAG prompts.
        """
        relevant_terms = self.search(query)
        
        if not relevant_terms:
            return ""
        
        context_parts = ["Relevant automotive terminology:"]
        for item in relevant_terms[:5]:  # Limit to top 5 terms
            context_parts.append(f"- {item['term']}: {item['definition']}")
        
        return "\n".join(context_parts)
    
    def get_all_definitions_text(self) -> str:
        """Get all definitions as a formatted text block."""
        parts = []
        
        for domain, terms in self.dictionaries.items():
            parts.append(f"\n## {domain} Terms\n")
            for term, definition in terms.items():
                parts.append(f"- **{term}**: {definition}")
        
        return "\n".join(parts)


# Singleton instance
_domain_dict_instance: Optional[DomainDictionary] = None


def get_domain_dictionary() -> DomainDictionary:
    """Get or create domain dictionary instance."""
    global _domain_dict_instance
    if _domain_dict_instance is None:
        _domain_dict_instance = DomainDictionary()
    return _domain_dict_instance
