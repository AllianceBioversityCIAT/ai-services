# CGIAR Institution Validation Rules

## 📋 Official Rules for Review Team

These are the official CGIAR rules for validating new institutions to be added to CLARISA.

---

### **Rule 1: Legal Entities**

All institutions should be **legal entities**, with exceptions for certain institutions which:
- Are NOT legal entities, BUT
- Detain a **significant research mandate** which is important to CGIAR

**What to do if not a legal entity:**
- Add the **closest organization** to which it is affiliated AND which IS a legal entity

**Examples:**
- ❌ **Earth Institute** (not a legal entity)  
  ✅ Add as: **Columbia University**

- ❌ **CCAFS** (not a legal entity)  
  ✅ Add as: **Alliance of Bioversity and CIAT**

> *Note: An institution might be required to be registered but does not have legal entity status.*

---

### **Rule 2: Bilateral Development Agencies**

Aid or development agencies receiving funding from governments in their home countries should be classified as:

**✅ Bilateral Development Agencies**  
(NOT as government entities)

**Examples:**
- USAID (United States Agency for International Development)
- DFID (UK Department for International Development)
- BMZ (German Federal Ministry for Economic Cooperation and Development)
- SIDA (Swedish International Development Cooperation Agency)

---

### **Rule 3: Government Entities**

Any **Ministry/Department/Agency** at the **national, state, or local level**, including parliamentary bodies, should be listed as:

**✅ Governmental Entities**

**Examples:**
- Ministry of Agriculture (any country)
- National Research Council
- State Department of Environment
- Municipal Agricultural Agency
- Parliamentary Committee on Agriculture

---

### **Rule 4: Financial Institutions**

Development banks and multilateral financing institutions should be classified as:

**✅ International/Regional Financial Institutions**

**Examples:**
- World Bank
- Asian Development Bank
- African Development Bank
- Inter-American Development Bank
- Global Environment Facility (GEF)
- Green Climate Fund

---

### **Rule 5: International/Regional Research Institutions**

Any **international or regional institution carrying out research**, regardless of its funding source (public or private), should be classified as:

**✅ International/Regional Research Institution**

**Includes:**
- Think tanks
- Research consulting firms
- International research centers

**Excludes:**
- ❌ CGIAR centers (separate category)

**Examples:**
- International Food Policy Research Institute (IFPRI) - if not CGIAR
- Stockholm Environment Institute (SEI)
- Overseas Development Institute (ODI)
- World Resources Institute (WRI)

---

### **Rule 6: National/Local Research Institutions**

Any **national or local institution carrying out research**, regardless of its funding source (public or private), should be classified as:

**✅ National/Local Research Institution**

**Excludes:**
- ❌ Academic institutions (separate category)

**Examples:**
- National Agricultural Research Institute
- State Research Center
- Local Research Foundation
- National Science Laboratory

---

### **Rule 7: UN Entities**

UN entities should be classified as:

**✅ International Organizations**

**Examples:**
- FAO (Food and Agriculture Organization)
- UNDP (United Nations Development Programme)
- UNEP (United Nations Environment Programme)
- WFP (World Food Programme)
- UNESCO
- UNICEF

---

## 📊 Quick Reference Table

| Institution Type | Classification | Funding Source | Examples |
|-----------------|----------------|----------------|----------|
| Universities | Academic Institution | Public/Private | MIT, Oxford, UNAM |
| National Research Centers | National/Local Research | Public/Private | INIA, EMBRAPA |
| International Research | International/Regional Research | Public/Private | SEI, ODI, WRI |
| CGIAR Centers | CGIAR Center | Mixed | CIMMYT, IRRI, ILRI |
| Ministries/Agencies | Government Entity | Public | Ministry of Agriculture |
| Aid Agencies | Bilateral Development Agency | Government (home country) | USAID, DFID, SIDA |
| Development Banks | International/Regional Financial | Multilateral | World Bank, ADB |
| UN Organizations | International Organization | UN | FAO, UNDP, WFP |
| NGOs | NGO | Donations/Mixed | Oxfam, Care, WWF |
| Private Companies | Private Company | Private | Monsanto, Syngenta |

---

## 🔍 Decision Tree

```
Is it a legal entity?
├─ YES
│  └─ What type?
│     ├─ University → Academic Institution
│     ├─ Research (National) → National/Local Research Institution
│     ├─ Research (International) → International/Regional Research Institution
│     ├─ Ministry/Department → Government Entity
│     ├─ Aid Agency (USAID, etc.) → Bilateral Development Agency
│     ├─ Development Bank → International/Regional Financial Institution
│     ├─ UN Entity → International Organization
│     ├─ NGO → NGO
│     └─ Company → Private Company
│
└─ NO (not a legal entity)
   └─ Does it have significant research mandate?
      ├─ YES → Find parent legal entity and add that
      │        (Example: Earth Institute → Columbia University)
      └─ NO → Do not add to CLARISA
```

---

## 💡 Important Notes

1. **Legal entity status is PRIMARY** - Always check this first
2. **Research mandate matters** - Exception for non-legal entities with significant research
3. **Funding source ≠ Classification** - A private-funded research center is still a research institution
4. **Be specific with government entities** - Aid agencies are NOT government entities
5. **CGIAR centers are special** - They don't fall into "International Research Institution"
6. **UN = International Organization** - Always classify UN entities this way
7. **Academic vs Research** - Universities are separate from research institutions

---

## 🎯 Application in Web Search

The web search module (`src/web_search.py`) uses these rules to extract relevant information:

### Information Collected:
1. ✅ Legal entity status
2. ✅ Parent organization (if not legal entity)
3. ✅ Specific institution type according to CGIAR classification
4. ✅ Research mandate

### Post-Search Validation:
- Review team can use extracted information to decide if institution qualifies
- Parent organization identified if not a legal entity
- Classification helps with proper categorization in CLARISA

---

## 📚 References

- CGIAR CLARISA Database: https://clarisa.cgiar.org/
- Internal review team guidelines (2026)

---

**Last Updated:** March 2, 2026
