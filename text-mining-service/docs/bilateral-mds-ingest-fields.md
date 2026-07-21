# MDS — campos obligatorios para creación de results (ingest / bilateral)

Documentación del **Minimum Data Set (MDS)** que los Centers deben enviar al crear un result vía el Normalizer (`POST /ingest`), que desemboca en `POST /api/bilateral/create`.

Fuente: [PRMS Normalizer – Technical Field Documentation](https://cgiar-prms.notion.site/PRMS-Normalizer-Technical-Field-Documentation-287f271224788055a0d9c2bc23b1a06b) + schema OpenAPI `ResultData`.

Leyenda:

| Símbolo | Significado |
|---|---|
| ✅ | Obligatorio (MDS) |
| ❌ | Opcional |
| ⚙️ | Condicional / al menos una alternativa |
| `min 1` | Si el array se envía (o es required), debe tener ≥ 1 ítem |

---

## 1. Envelope de la request

```json
{
  "tenant": "prms.result-management.api",
  "op": "dataset.ingest.requested",
  "results": [
    {
      "type": "<result_type>",
      "data": { }
    }
  ]
}
```

| Campo | Tipo | MDS | Notas |
|---|---|---|---|
| `tenant` | `string` | ✅ | Identificador del sistema emisor |
| `op` | `string` | ✅ | `dataset.ingest.requested` \| `update` \| `delete` |
| `results` | `array` | ✅ | Lista de results a procesar |
| `results[].type` | `string` | ✅ | Ver tipos admitidos abajo |
| `results[].data` | `object` | ✅ | Common fields + bloque type-specific |

### Tipos admitidos (`results[].type`)

| `type` | Bloque type-specific en `data` |
|---|---|
| `knowledge_product` | `knowledge_product` |
| `capacity_sharing` | `capacity_sharing` |
| `innovation_development` | `innovation_development` |
| `innovation_use` | `innovation_use` |
| `policy_change` | `policy_change` |
| `other_output` | — (solo common fields) |
| `other_outcome` | — (solo common fields) |

---

## 2. Common fields (todos los tipos)

Ubicación: raíz de `data`.

### 2.1 Resumen MDS

| Campo | Tipo | MDS | Estructura |
|---|---|---|---|
| `created_date` | `string` (ISO date) | ✅ | — |
| `created_by` | `object` | ✅ | ver §2.2 |
| `submitted_by` | `object` | ✅ | ver §2.3 |
| `lead_center` | `object` | ✅ | ver §2.4 |
| `title` | `string` | ✅ | max ~30 words |
| `description` | `string` | ✅ | max ~150 words |
| `toc_mapping` | `object` | ✅ | ver §2.5 |
| `geo_focus` | `object` | ✅ | ver §2.6 |
| `contributing_center` | `array[object]` | ✅ `min 1` | ver §2.7 |
| `contributing_partners` | `array[object]` | ✅ `min 1` | ver §2.8 |
| `contributing_bilateral_projects` | `array[object]` | ✅ `min 1` | ver §2.9 |
| `contributing_programs` | `array[object]` | ❌ | ver §2.10 |
| `evidence` | `array[object]` | ❌ (si se envía: `min 1`) | ver §2.11 |

### 2.2 `created_by` (object, ✅)

```json
{
  "email": "j.doe@cgiar.org",
  "name": "John Doe"
}
```

| Campo | Tipo | MDS |
|---|---|---|
| `email` | `string` (email) | ✅ |
| `name` | `string` | ✅ |

### 2.3 `submitted_by` (object, ✅)

```json
{
  "email": "j.doe@cgiar.org",
  "name": "John Doe",
  "submitted_date": "2025-10-09T12:00:00Z",
  "comment": "Initial batch upload from STAR"
}
```

| Campo | Tipo | MDS |
|---|---|---|
| `email` | `string` (email) | ✅ |
| `name` | `string` | ✅ |
| `submitted_date` | `string` (ISO date) | ✅ |
| `comment` | `string` | ❌ |

### 2.4 `lead_center` (object, ✅)

Al menos **uno** de: `name` | `acronym` | `institution_id`.

```json
{
  "institution_id": 115,
  "acronym": "CIFOR",
  "name": "Center for International Forestry Research"
}
```

| Campo | Tipo | MDS |
|---|---|---|
| `institution_id` | `number` | ⚙️ al menos uno |
| `acronym` | `string` | ⚙️ al menos uno |
| `name` | `string` | ⚙️ al menos uno |

### 2.5 `toc_mapping` (object, ✅)

```json
{
  "science_program_id": "SP12",
  "aow_compose_code": "SP12-AOW01",
  "result_title": "Adoption of improved seed varieties",
  "result_indicator_description": "Share of farmers adopting improved seeds",
  "result_indicator_type_name": "# Of Knowledge Products"
}
```

| Campo | Tipo | MDS |
|---|---|---|
| `science_program_id` | `string` | ✅ (`SP01`–`SP13`) |
| `aow_compose_code` | `string` | ❌ |
| `result_title` | `string` | ❌ |
| `result_indicator_description` | `string` | ❌ |
| `result_indicator_type_name` | `string` | ❌ |

### 2.6 `geo_focus` (object, ✅)

Al menos **uno** de: `scope_code` | `scope_label`.

```json
{
  "scope_code": 4,
  "scope_label": "National",
  "regions": [{ "um49code": 145, "name": "Sub-Saharan Africa" }],
  "countries": [{ "id": 170, "name": "Colombia", "iso_alpha_3": "COL", "iso_alpha_2": "CO" }],
  "subnational_areas": [{ "id": 1, "name": "Nairobi County" }]
}
```

| Campo | Tipo | MDS |
|---|---|---|
| `scope_code` | `number` | ⚙️ (`1`\|`2`\|`3`\|`4`\|`5`\|`50`) |
| `scope_label` | `string` | ⚙️ (`Global`\|`Regional`\|`Multi-national`\|`National`\|`Sub-national`\|`This is yet to be determined`) |
| `regions` | `array[object]` | Condicional — ver tabla abajo |
| `countries` | `array[object]` | Condicional — ver tabla abajo |
| `subnational_areas` | `array[object]` | Condicional — ver tabla abajo |

#### Reglas por `scope_code`

| Code | Label | Regla |
|---|---|---|
| `1` | Global | **No** enviar `regions`, `countries` ni `subnational_areas` |
| `2` | Regional | `regions` ✅ `min 1` |
| `3` | Multi-national | `countries` ✅ `min 2` |
| `4` | National | `countries` ✅ `min 1` |
| `5` | Sub-national | `countries` ✅ `min 1` **y** `subnational_areas` ✅ `min 1` |
| `50` | TBD | Sin geo adicional |

#### Ítem de `regions[]`

Al menos **uno** de: `um49code` | `name`.

| Campo | Tipo | MDS |
|---|---|---|
| `um49code` | `number` | ⚙️ al menos uno |
| `name` | `string` | ⚙️ al menos uno |

#### Ítem de `countries[]`

Al menos **uno** de: `id` | `name` | `iso_alpha_3` | `iso_alpha_2`.

| Campo | Tipo | MDS |
|---|---|---|
| `id` | `number` | ⚙️ al menos uno |
| `name` | `string` | ⚙️ al menos uno |
| `iso_alpha_3` | `string` (len 3) | ⚙️ al menos uno |
| `iso_alpha_2` | `string` (len 2) | ⚙️ al menos uno |

#### Ítem de `subnational_areas[]`

Al menos **uno** de: `id` | `name`.

| Campo | Tipo | MDS |
|---|---|---|
| `id` | `number` | ⚙️ al menos uno |
| `name` | `string` | ⚙️ al menos uno |

### 2.7 `contributing_center` (array[object], ✅ `min 1`)

Cada ítem: al menos **uno** de `institution_id` | `acronym` | `name`.

```json
[
  { "institution_id": 1279, "acronym": "ICARDA" },
  { "acronym": "CIFOR" }
]
```

| Campo (por ítem) | Tipo | MDS |
|---|---|---|
| `institution_id` | `number` | ⚙️ al menos uno |
| `acronym` | `string` | ⚙️ al menos uno |
| `name` | `string` | ⚙️ al menos uno |

### 2.8 `contributing_partners` (array[object], ✅ `min 1`)

Misma forma que `contributing_center`.

```json
[
  { "institution_id": 7, "acronym": "NARO" }
]
```

| Campo (por ítem) | Tipo | MDS |
|---|---|---|
| `institution_id` | `number` | ⚙️ al menos uno |
| `acronym` | `string` | ⚙️ al menos uno |
| `name` | `string` | ⚙️ al menos uno |

### 2.9 `contributing_bilateral_projects` (array[object], ✅ `min 1`)

```json
[
  {
    "grant_title": "Seed Innovation Window",
    "is_lead": false,
    "usd_budget": 15000,
    "is_determined": false
  }
]
```

| Campo (por ítem) | Tipo | MDS | Notas |
|---|---|---|---|
| `grant_title` | `string` | ✅ | Título del proyecto bilateral / NPP |
| `is_lead` | `boolean` | ❌ | Flag de lead |
| `usd_budget` | `number` | ❌ | Solo **Innovation Use** |
| `is_determined` | `boolean` | ❌ | Solo **Innovation Use** (`true` → budget TBD / null) |

### 2.10 `contributing_programs` (array[object], ❌)

Si se envía, cada ítem exige `science_program_id`.

```json
[
  {
    "science_program_id": "SP02",
    "aow_compose_code": "SP02-AOW03",
    "result_title": "Nutrition outcomes improved",
    "result_indicator_description": "Households reached with nutrition interventions",
    "result_indicator_type_name": "Outcome"
  }
]
```

| Campo (por ítem) | Tipo | MDS |
|---|---|---|
| `science_program_id` | `string` | ✅ |
| `aow_compose_code` | `string` | ❌ |
| `result_title` | `string` | ❌ |
| `result_indicator_description` | `string` | ❌ |
| `result_indicator_type_name` | `string` | ❌ |

### 2.11 `evidence` (array[object], ❌; si se envía: `min 1`)

```json
[
  {
    "link": "https://example.org/paper-123",
    "description": "Peer-reviewed article summarizing multi-country trials."
  }
]
```

| Campo (por ítem) | Tipo | MDS |
|---|---|---|
| `link` | `string` (URI) | ✅ |
| `description` | `string` | ❌ |

---

## 3. Type-specific sections

Además de common fields, cada tipo (excepto `other_output` / `other_outcome`) debe incluir su bloque.

---

### 3.1 Knowledge Product — `data.knowledge_product`

```json
{
  "knowledge_product": {
    "handle": "hdl:20.500.12345/abc-2025"
  }
}
```

| Campo | Tipo | MDS | Notas |
|---|---|---|---|
| `handle` | `string` | ✅ | Handle / DOI; en PRMS se usa para obtener metadata de CGSpace |

Campos que aparecen en ejemplos pero **no** son MDS en Notion: `knowledge_product_type`, `metadataCG`, `licence`, `agrovoc_keywords`.

---

### 3.2 Capacity Sharing — `data.capacity_sharing`

```json
{
  "capacity_sharing": {
    "number_people_trained": {
      "women": 25,
      "men": 18,
      "non_binary": 2,
      "unknown": 5
    },
    "length_training": "Short-term",
    "delivery_method": "Blended (in-person and virtual)"
  }
}
```

| Campo | Tipo | MDS |
|---|---|---|
| `number_people_trained` | `object` | ✅ |
| `length_training` | `string` (enum) | ✅ |
| `delivery_method` | `string` (enum) | ✅ |

#### `number_people_trained`

Al menos **uno** de los cuatro campos.

| Campo | Tipo | MDS |
|---|---|---|
| `women` | `number` | ⚙️ al menos uno |
| `men` | `number` | ⚙️ al menos uno |
| `non_binary` | `number` | ⚙️ al menos uno |
| `unknown` | `number` | ⚙️ al menos uno |

#### `length_training` (enum)

| Valor |
|---|
| `PhD` |
| `Master` |
| `Short-term` |
| `Long-term` |

#### `delivery_method` (enum)

| Valor |
|---|
| `Virtual / Online` |
| `In person` |
| `Blended (in-person and virtual)` |

---

### 3.3 Innovation Development — `data.innovation_development`

```json
{
  "innovation_development": {
    "innovation_typology": {
      "code": 12,
      "name": "Technological innovation"
    },
    "innovation_developers": "John Doe; Marie Curie; CGIAR Breeding Team",
    "innovation_readiness_level": {
      "id": 14,
      "name": "Phase 3 - Available for uptake"
    }
  }
}
```

| Campo | Tipo | MDS (Notion) | Notas |
|---|---|---|---|
| `innovation_typology` | `object` | ✅ | `code` **o** `name` |
| `innovation_readiness_level` | `object` | ✅ | `id` **o** `name` |
| `innovation_developers` | `string` | ❌ | En PRMS bilateral (`create`) sí es obligatorio |

#### `innovation_typology`

| Campo | Tipo | MDS |
|---|---|---|
| `code` | `number` | ⚙️ al menos uno |
| `name` | `string` | ⚙️ al menos uno |

#### `innovation_readiness_level`

| Campo | Tipo | MDS |
|---|---|---|
| `id` | `number` | ⚙️ al menos uno |
| `name` | `string` | ⚙️ al menos uno |

---

### 3.4 Innovation Use — `data.innovation_use`

```json
{
  "innovation_use": {
    "current_innovation_use_numbers": {
      "innov_use_to_be_determined": false,
      "actors": [ ],
      "organization": [ ],
      "measures": [ ]
    },
    "innovation_use_level": {
      "level": 2,
      "name": "Proven under field conditions"
    }
  }
}
```

| Campo | Tipo | MDS |
|---|---|---|
| `current_innovation_use_numbers` | `object` | ✅ |
| `innovation_use_level` | `object` | ❌ |

#### `current_innovation_use_numbers`

| Campo | Tipo | MDS |
|---|---|---|
| `innov_use_to_be_determined` | `boolean` | ✅ |
| `actors` | `array[object]` | ⚙️ si `innov_use_to_be_determined = false` → al menos uno de `actors` / `organization` / `measures` |
| `organization` | `array[object]` | ⚙️ (mismo) |
| `measures` | `array[object]` | ⚙️ (mismo) |

**Regla:**

- `innov_use_to_be_determined = true` → no se exigen `actors` / `organization` / `measures`.
- `innov_use_to_be_determined = false` → se exige al menos uno de esos arrays.

#### Ítem de `actors[]`

```json
{
  "actor_type_id": 1,
  "actor_type_name": "Farmers/ (agro)pastoralist/ herders/ fishers",
  "sex_and_age_disaggregation": true,
  "how_many": 120,
  "women": 60,
  "women_youth": 25,
  "men": 40,
  "men_youth": 15,
  "other_actor_type": null,
  "previousWomen": 50
}
```

| Campo | Tipo | MDS |
|---|---|---|
| `actor_type_id` | `string` \| `integer` | ⚙️ al menos uno con `actor_type_name` |
| `actor_type_name` | `string` | ⚙️ al menos uno con `actor_type_id` |
| `other_actor_type` | `string` \| `null` | Condicional: ✅ si `actor_type_id = 5` |
| `sex_and_age_disaggregation` | `boolean` \| `null` | ❌ |
| `how_many` | `string` \| `integer` \| `null` | Condicional: ✅ si `sex_and_age_disaggregation = true` |
| `result_actors_id` | `string` \| `integer` | ❌ |
| `women` | `string` \| `integer` \| `null` | ❌ |
| `women_youth` | `string` \| `integer` \| `null` | ❌ |
| `men` | `string` \| `integer` \| `null` | ❌ |
| `men_youth` | `string` \| `integer` \| `null` | ❌ |
| `previousWomen` | `string` \| `integer` \| `null` | ❌ |

Actor types de referencia: `1` Farmers…, `2` Researchers, `3` Extension agents, `4` Policy actors, `5` Other.

#### Ítem de `organization[]`

```json
{
  "institution_types_id": 39,
  "institution_types_name": "Research Center",
  "institution_sub_type_id": 39,
  "institution_sub_type_name": "International Research Center",
  "other_institution": null,
  "how_many": 3,
  "hide": false
}
```

| Campo | Tipo | MDS |
|---|---|---|
| `institution_types_id` | `string` \| `integer` | ⚙️ al menos uno con `institution_types_name` |
| `institution_types_name` | `string` | ⚙️ al menos uno con `institution_types_id` |
| `other_institution` | `string` \| `null` | Condicional: ✅ si `institution_types_id = 78` |
| `institution_sub_type_id` | `string` \| `integer` \| `null` | ❌ |
| `institution_sub_type_name` | `string` | ❌ |
| `how_many` | `string` \| `integer` \| `null` | ❌ |
| `hide` | `boolean` | ❌ |

#### Ítem de `measures[]`

```json
{
  "unit_of_measure": "hectares",
  "quantity": "2500"
}
```

| Campo | Tipo | MDS |
|---|---|---|
| `unit_of_measure` | `string` | ✅ |
| `quantity` | `string` \| `number` | ❌ |

---

### 3.5 Policy Change — `data.policy_change`

```json
{
  "policy_change": {
    "policy_type": {
      "id": 1,
      "name": "Budget or investment",
      "status_amount": { "id": 2, "name": "Increased" },
      "amount": 500000
    },
    "policy_stage": {
      "id": 3,
      "name": "Implemented"
    },
    "implementing_organization": [
      {
        "institutions_id": 1279,
        "institutions_acronym": "ICARDA",
        "institutions_name": "International Center for Agricultural Research in the Dry Areas"
      }
    ]
  }
}
```

| Campo | Tipo | MDS |
|---|---|---|
| `policy_type` | `object` | ✅ |
| `policy_stage` | `object` | ✅ |
| `implementing_organization` | `array[object]` | ✅ `min 1` |

#### `policy_type`

| Campo | Tipo | MDS |
|---|---|---|
| `id` | `integer` | ⚙️ al menos uno con `name` |
| `name` | `string` | ⚙️ al menos uno con `id` |
| `status_amount` | `object` | Condicional: ✅ si `id = 1` |
| `amount` | `integer` | Condicional: ✅ si `id = 1` |

Si `policy_type.id ≠ 1` → **no** enviar `status_amount` ni `amount`.

#### `status_amount` (solo si `policy_type.id = 1`)

| Campo | Tipo | MDS |
|---|---|---|
| `id` | `integer` | ⚙️ al menos uno |
| `name` | `string` | ⚙️ al menos uno |

#### `policy_stage`

| Campo | Tipo | MDS |
|---|---|---|
| `id` | `integer` | ⚙️ al menos uno |
| `name` | `string` | ⚙️ al menos uno |

#### Ítem de `implementing_organization[]`

Al menos **uno** de: `institutions_id` | `institutions_acronym` | `institutions_name`.

| Campo | Tipo | MDS |
|---|---|---|
| `institutions_id` | `integer` | ⚙️ al menos uno |
| `institutions_acronym` | `string` | ⚙️ al menos uno |
| `institutions_name` | `string` | ⚙️ al menos uno |

---

### 3.6 Other Output / Other Outcome

Sin bloque type-specific. Solo aplican **common fields** (§2).

---

## 4. Checklist rápido por tipo

| Campo MDS | KP | Cap Sharing | Innov Dev | Innov Use | Policy | Other Out/Outc |
|---|---|---|---|---|---|---|
| Common fields §2.1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `knowledge_product.handle` | ✅ | — | — | — | — | — |
| `capacity_sharing.*` | — | ✅ | — | — | — | — |
| `innovation_development.typology` + `readiness` | — | — | ✅ | — | — | — |
| `innovation_use.current_innovation_use_numbers` | — | — | — | ✅ | — | — |
| `policy_change.*` | — | — | — | — | ✅ | — |

---

## 5. Notas de alineación con PRMS bilateral (`POST /api/bilateral/create`)

El Normalizer documenta el contrato MDS “de Centers”. En PRMS (`CreateBilateralDto` / handlers) hay diferencias útiles a tener en cuenta:

| Tema | Normalizer (Notion / OpenAPI) | PRMS bilateral |
|---|---|---|
| Discriminator | `results[].type` (string) | También exige `data.result_type_id` (+ `result_level_id`) |
| KP `title` / `description` / `geo_focus` | ✅ required | Opcionales (se toman de CGSpace vía `handle`) |
| `contributing_center` / `contributing_partners` | ✅ required `min 1` | Opcionales en DTO |
| `evidence` | Opcional; si va, `min 1` | Opcional |
| `innovation_developers` | ❌ en Notion | ✅ required en handler/DTO |
| KP type-specific | Solo `handle` MDS | Solo `handle` requerido |

Implementación: `src/api/bilateral/dto/create-bilateral.dto.ts` + `handlers/*`.

---

## 6. Referencias

- Notion: [PRMS Normalizer – Technical Field Documentation](https://cgiar-prms.notion.site/PRMS-Normalizer-Technical-Field-Documentation-287f271224788055a0d9c2bc23b1a06b)
- OpenAPI TEST: `https://v2f4lv8av4.execute-api.us-east-1.amazonaws.com/openapi.json` (`ResultData`)
- Payload de respuesta (read): [`bilateral-result-summaries.en.md`](./bilateral-result-summaries.en.md)
- Endpoint creación: `src/api/bilateral/bilateral.controller.ts` → `POST /create`
