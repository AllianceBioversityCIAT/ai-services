"""
Example script to test Web Search functionality
Run this to verify that OpenAI Web Search is working correctly
"""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.web_search import test_search

print("=" * 80)
print("🧪 WEB SEARCH - TESTING EXAMPLES")
print("=" * 80)
print()

# =============================================================================
# Example 1: University with website (Focused Search)
# =============================================================================
print("📚 Example 1: University with website")
test_search(
    name="Stanford University",
    country="United States",
    website="https://www.stanford.edu"
)

# =============================================================================
# Example 2: Research Center with website (Focused Search)
# =============================================================================
print("📚 Example 2: Research center with website")
test_search(
    name="CIMMYT",
    country="Mexico",
    website="https://www.cimmyt.org"
)

# =============================================================================
# Example 3: Institution without website (Open Search)
# =============================================================================
print("📚 Example 3: Institution without website")
test_search(
    name="Instituto Nacional de Investigación Agropecuaria",
    country="Uruguay"
)

# =============================================================================
# Example 4: International Organization
# =============================================================================
print("📚 Example 4: International organization")
test_search(
    name="Food and Agriculture Organization",
    country="Italy",
    website="https://www.fao.org"
)

# =============================================================================
# Example 5: Research Unit (NOT Legal Entity)
# =============================================================================
print("📚 Example 5: Research Unit (NOT Legal Entity)")
test_search(
    name="Earth Institute",
    country="United States"
)


print("=" * 80)
print("✅ TESTING COMPLETED")
print("=" * 80)
print()
print("💡 Notes:")
print("   - Focused searches (with website) are more accurate and faster")
print("   - Open searches work well when the institution has strong web presence")
print("   - Check the sources to verify data quality")
print()