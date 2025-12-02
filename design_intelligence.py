"""
🔮 Sistema de Inteligencia de Diseño para Landing Pages Esotéricas
===================================================================

Este módulo analiza las keywords del grupo de anuncios y genera diseños
únicos, variados e impactantes especializados en el nicho esotérico.

OBJETIVO: El usuario solo selecciona campaña + grupo de anuncios, y el 
sistema automáticamente genera un diseño sorprendente y diferente cada vez.

Autor: Sistema IA Enterprise
Versión: 1.0.0
"""

import os
import random
import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

# =============================================================================
# CATEGORÍAS ESOTÉRICAS Y SUS ATMÓSFERAS
# =============================================================================

class EsotericCategory(Enum):
    """Categorías principales del nicho esotérico."""
    AMOR_AMARRES = "amor_amarres"           # Amarres de amor, hechizos románticos
    TAROT_ADIVINACION = "tarot_adivinacion" # Tarot, videncia, lectura de cartas
    BRUJERIA_MAGIA = "brujeria_magia"       # Brujos, magia, rituales
    SANTERIA_VUDÚ = "santeria_vudu"         # Santería, vudú, orishas
    PROTECCION_LIMPIEZA = "proteccion_limpieza" # Limpiezas, protección, barridas
    PROSPERIDAD_DINERO = "prosperidad_dinero"   # Dinero, abundancia, negocios
    VENGANZA_SEPARACION = "venganza_separacion" # Separaciones, alejamientos
    SALUD_SANACION = "salud_sanacion"       # Curanderos, sanación espiritual
    ESPIRITISMO = "espiritismo"             # Médiums, contacto espiritual


@dataclass
class DesignAtmosphere:
    """Define la atmósfera visual completa para una categoría."""
    name: str
    primary_colors: List[str]
    secondary_colors: List[str]
    accent_colors: List[str]
    gradient_styles: List[str]
    icon_set: List[str]  # Emojis/símbolos representativos
    animation_intensity: str  # "subtle", "moderate", "intense"
    visual_elements: List[str]  # "particles", "candles", "smoke", etc.
    font_pairing: Dict[str, str]  # {"heading": "font", "body": "font"}
    mood_keywords: List[str]
    background_style: str  # "dark_mystical", "warm_ritual", "cosmic", etc.


# Base de datos de atmósferas por categoría
ATMOSPHERES: Dict[EsotericCategory, List[DesignAtmosphere]] = {
    EsotericCategory.AMOR_AMARRES: [
        DesignAtmosphere(
            name="Pasión Ardiente",
            primary_colors=["#DC2626", "#B91C1C", "#991B1B"],  # Rojos intensos
            secondary_colors=["#F472B6", "#EC4899", "#DB2777"],  # Rosas
            accent_colors=["#FFD700", "#FCD34D", "#FBBF24"],  # Dorados
            gradient_styles=[
                "linear-gradient(135deg, #DC2626 0%, #991B1B 50%, #7F1D1D 100%)",
                "radial-gradient(circle at 30% 30%, rgba(220, 38, 38, 0.8), rgba(127, 29, 29, 0.9))",
                "linear-gradient(to right, #B91C1C, #DC2626, #EF4444)"
            ],
            icon_set=["💕", "🔥", "❤️‍🔥", "💋", "🌹", "💘", "✨"],
            animation_intensity="intense",
            visual_elements=["hearts_floating", "rose_petals", "candle_flames", "red_smoke"],
            font_pairing={"heading": "Playfair Display", "body": "Lato"},
            mood_keywords=["pasión", "amor eterno", "unión", "deseo", "atracción"],
            background_style="warm_romantic"
        ),
        DesignAtmosphere(
            name="Luna Rosa",
            primary_colors=["#DB2777", "#BE185D", "#9D174D"],
            secondary_colors=["#A855F7", "#9333EA", "#7C3AED"],
            accent_colors=["#FDF2F8", "#FCE7F3", "#FBCFE8"],
            gradient_styles=[
                "linear-gradient(180deg, #1E1B4B 0%, #3B0764 50%, #9D174D 100%)",
                "radial-gradient(ellipse at top, #BE185D, #581C87)"
            ],
            icon_set=["🌙", "💖", "🦋", "🌸", "💜", "✨", "🔮"],
            animation_intensity="moderate",
            visual_elements=["moon_phases", "butterflies", "pink_aura", "stars"],
            font_pairing={"heading": "Cormorant Garamond", "body": "Quicksand"},
            mood_keywords=["romance", "conexión", "destino", "luna", "magia rosa"],
            background_style="cosmic_romantic"
        ),
        DesignAtmosphere(
            name="Fuego Eterno",
            primary_colors=["#F97316", "#EA580C", "#C2410C"],
            secondary_colors=["#DC2626", "#B91C1C", "#991B1B"],
            accent_colors=["#FEF3C7", "#FDE68A", "#FCD34D"],
            gradient_styles=[
                "linear-gradient(to bottom, #1C1917 0%, #44403C 30%, #F97316 100%)",
                "radial-gradient(circle at bottom, #EA580C, #1C1917)"
            ],
            icon_set=["🔥", "💕", "⚡", "🖤", "❤️‍🔥", "🌋"],
            animation_intensity="intense",
            visual_elements=["fire_particles", "ember_glow", "heat_waves", "smoke_rising"],
            font_pairing={"heading": "Oswald", "body": "Source Sans Pro"},
            mood_keywords=["intenso", "poderoso", "irresistible", "fuego", "pasión"],
            background_style="dark_fire"
        ),
    ],
    
    EsotericCategory.TAROT_ADIVINACION: [
        DesignAtmosphere(
            name="Arcanos Místicos",
            primary_colors=["#6D28D9", "#7C3AED", "#8B5CF6"],
            secondary_colors=["#FFD700", "#F59E0B", "#D97706"],
            accent_colors=["#E0E7FF", "#C7D2FE", "#A5B4FC"],
            gradient_styles=[
                "linear-gradient(135deg, #0F172A 0%, #1E1B4B 50%, #312E81 100%)",
                "conic-gradient(from 180deg, #4C1D95, #1E1B4B, #4C1D95)"
            ],
            icon_set=["🔮", "🃏", "⭐", "🌙", "👁️", "✨", "🌟"],
            animation_intensity="moderate",
            visual_elements=["crystal_ball_glow", "card_shuffle", "stars_twinkling", "mystic_smoke"],
            font_pairing={"heading": "Cinzel", "body": "Outfit"},
            mood_keywords=["destino", "futuro", "revelación", "clarividencia", "misterio"],
            background_style="cosmic_mystical"
        ),
        DesignAtmosphere(
            name="Oráculo Celestial",
            primary_colors=["#1E3A8A", "#1D4ED8", "#2563EB"],
            secondary_colors=["#A855F7", "#9333EA", "#7C3AED"],
            accent_colors=["#FEF9C3", "#FEF08A", "#FDE047"],
            gradient_styles=[
                "linear-gradient(to top, #0C0A1D 0%, #1E1B4B 50%, #1E3A8A 100%)",
                "radial-gradient(ellipse at center, #1D4ED8, #0F172A)"
            ],
            icon_set=["🌌", "⭐", "🔭", "🌠", "💫", "🌙", "✨"],
            animation_intensity="subtle",
            visual_elements=["constellation_lines", "shooting_stars", "nebula_clouds", "zodiac_symbols"],
            font_pairing={"heading": "Spectral", "body": "Inter"},
            mood_keywords=["celestial", "cósmico", "astros", "universo", "infinito"],
            background_style="deep_space"
        ),
    ],
    
    EsotericCategory.BRUJERIA_MAGIA: [
        DesignAtmosphere(
            name="Aquelarre Nocturno",
            primary_colors=["#18181B", "#27272A", "#3F3F46"],
            secondary_colors=["#16A34A", "#15803D", "#166534"],
            accent_colors=["#A855F7", "#9333EA", "#7C3AED"],
            gradient_styles=[
                "linear-gradient(180deg, #09090B 0%, #18181B 50%, #27272A 100%)",
                "radial-gradient(circle at 50% 50%, #166534, #09090B)"
            ],
            icon_set=["🧙‍♂️", "🌙", "🕯️", "🦇", "🍃", "⚗️", "📜"],
            animation_intensity="moderate",
            visual_elements=["candles_flickering", "herbs_floating", "cauldron_bubbles", "moon_glow"],
            font_pairing={"heading": "EB Garamond", "body": "Crimson Text"},
            mood_keywords=["ancestral", "poder", "ritual", "noche", "secreto"],
            background_style="dark_forest"
        ),
        DesignAtmosphere(
            name="Magia Ancestral",
            primary_colors=["#44403C", "#57534E", "#78716C"],
            secondary_colors=["#854D0E", "#A16207", "#CA8A04"],
            accent_colors=["#DC2626", "#EF4444", "#F87171"],
            gradient_styles=[
                "linear-gradient(135deg, #1C1917 0%, #292524 50%, #44403C 100%)",
                "radial-gradient(ellipse at bottom, #854D0E, #1C1917)"
            ],
            icon_set=["🔥", "📿", "🕯️", "🌿", "💀", "⚱️", "🗝️"],
            animation_intensity="subtle",
            visual_elements=["ancient_runes", "fire_glow", "dust_particles", "parchment_texture"],
            font_pairing={"heading": "Uncial Antiqua", "body": "Merriweather"},
            mood_keywords=["antiguo", "poder", "sabiduría", "ritual", "tradición"],
            background_style="ancient_temple"
        ),
        DesignAtmosphere(
            name="Bruja Moderna",
            primary_colors=["#581C87", "#6B21A8", "#7C3AED"],
            secondary_colors=["#0D9488", "#14B8A6", "#2DD4BF"],
            accent_colors=["#FCD34D", "#FBBF24", "#F59E0B"],
            gradient_styles=[
                "linear-gradient(to right, #0F172A, #1E1B4B, #581C87)",
                "conic-gradient(from 90deg, #6B21A8, #0D9488, #6B21A8)"
            ],
            icon_set=["🌙", "🔮", "✨", "🌿", "💜", "🦋", "⚡"],
            animation_intensity="moderate",
            visual_elements=["neon_glow", "crystal_shine", "modern_particles", "gradient_orbs"],
            font_pairing={"heading": "Poppins", "body": "DM Sans"},
            mood_keywords=["moderno", "poderoso", "chic", "místico", "elegante"],
            background_style="modern_mystic"
        ),
    ],
    
    EsotericCategory.SANTERIA_VUDÚ: [
        DesignAtmosphere(
            name="Altar de Orishas",
            primary_colors=["#DC2626", "#B91C1C", "#991B1B"],
            secondary_colors=["#FBBF24", "#F59E0B", "#D97706"],
            accent_colors=["#F8FAFC", "#F1F5F9", "#E2E8F0"],
            gradient_styles=[
                "linear-gradient(180deg, #1C1917 0%, #44403C 30%, #DC2626 100%)",
                "radial-gradient(circle at center, #B91C1C, #1C1917)"
            ],
            icon_set=["🔥", "🌴", "🥥", "🍯", "⚡", "🎭", "🌺"],
            animation_intensity="intense",
            visual_elements=["candle_altar", "tribal_patterns", "smoke_wisps", "ceremonial_drums"],
            font_pairing={"heading": "Abril Fatface", "body": "Roboto"},
            mood_keywords=["orishas", "poder", "tradición", "África", "espíritus"],
            background_style="ritual_altar"
        ),
        DesignAtmosphere(
            name="Vudú Profundo",
            primary_colors=["#18181B", "#1F2937", "#374151"],
            secondary_colors=["#7C3AED", "#8B5CF6", "#A78BFA"],
            accent_colors=["#DC2626", "#EF4444", "#F87171"],
            gradient_styles=[
                "linear-gradient(135deg, #09090B 0%, #18181B 100%)",
                "radial-gradient(circle at 30% 70%, #7C3AED, #09090B)"
            ],
            icon_set=["💀", "🕯️", "🐍", "🌙", "⚰️", "🖤", "🔮"],
            animation_intensity="subtle",
            visual_elements=["voodoo_dolls_shadow", "candle_drips", "snake_patterns", "skull_glow"],
            font_pairing={"heading": "Creepster", "body": "Josefin Sans"},
            mood_keywords=["oscuro", "misterioso", "poderoso", "ancestral", "oculto"],
            background_style="dark_voodoo"
        ),
    ],
    
    EsotericCategory.PROTECCION_LIMPIEZA: [
        DesignAtmosphere(
            name="Escudo de Luz",
            primary_colors=["#F8FAFC", "#F1F5F9", "#E2E8F0"],
            secondary_colors=["#FFD700", "#F59E0B", "#FBBF24"],
            accent_colors=["#3B82F6", "#2563EB", "#1D4ED8"],
            gradient_styles=[
                "linear-gradient(to bottom, #FEFCE8 0%, #FEF9C3 50%, #FDE68A 100%)",
                "radial-gradient(ellipse at top, #F8FAFC, #FBBF24)"
            ],
            icon_set=["✨", "🛡️", "⚡", "🌟", "💫", "🙏", "👁️"],
            animation_intensity="subtle",
            visual_elements=["light_rays", "golden_aura", "shield_glow", "sparkles"],
            font_pairing={"heading": "Marcellus", "body": "Open Sans"},
            mood_keywords=["protección", "luz", "pureza", "defensa", "energía"],
            background_style="divine_light"
        ),
        DesignAtmosphere(
            name="Purificación Espiritual",
            primary_colors=["#0D9488", "#14B8A6", "#2DD4BF"],
            secondary_colors=["#F8FAFC", "#F1F5F9", "#E2E8F0"],
            accent_colors=["#A855F7", "#9333EA", "#7C3AED"],
            gradient_styles=[
                "linear-gradient(180deg, #042F2E 0%, #134E4A 50%, #0D9488 100%)",
                "radial-gradient(circle at center, #14B8A6, #042F2E)"
            ],
            icon_set=["🌿", "💧", "🌊", "🍃", "🪶", "🌙", "✨"],
            animation_intensity="moderate",
            visual_elements=["water_ripples", "sage_smoke", "feather_float", "cleansing_waves"],
            font_pairing={"heading": "Cormorant", "body": "Nunito"},
            mood_keywords=["limpieza", "renovación", "agua", "naturaleza", "sanación"],
            background_style="water_purification"
        ),
    ],
    
    EsotericCategory.PROSPERIDAD_DINERO: [
        DesignAtmosphere(
            name="Abundancia Dorada",
            primary_colors=["#FFD700", "#F59E0B", "#D97706"],
            secondary_colors=["#16A34A", "#15803D", "#166534"],
            accent_colors=["#FEFCE8", "#FEF9C3", "#FEF08A"],
            gradient_styles=[
                "linear-gradient(135deg, #14532D 0%, #166534 50%, #D97706 100%)",
                "radial-gradient(circle at 70% 30%, #FFD700, #14532D)"
            ],
            icon_set=["💰", "💵", "🌟", "🍀", "✨", "👑", "💎"],
            animation_intensity="moderate",
            visual_elements=["gold_coins_falling", "money_glow", "lucky_sparkles", "crown_shine"],
            font_pairing={"heading": "Bodoni Moda", "body": "Montserrat"},
            mood_keywords=["riqueza", "abundancia", "éxito", "fortuna", "prosperidad"],
            background_style="golden_wealth"
        ),
        DesignAtmosphere(
            name="Flujo de Prosperidad",
            primary_colors=["#16A34A", "#22C55E", "#4ADE80"],
            secondary_colors=["#FFD700", "#F59E0B", "#FBBF24"],
            accent_colors=["#F0FDF4", "#DCFCE7", "#BBF7D0"],
            gradient_styles=[
                "linear-gradient(to right, #052E16 0%, #14532D 50%, #166534 100%)",
                "linear-gradient(135deg, #14532D, #22C55E, #16A34A)"
            ],
            icon_set=["🌱", "💵", "🌿", "💫", "🍀", "🌳", "💰"],
            animation_intensity="subtle",
            visual_elements=["growing_plants", "flowing_energy", "nature_prosperity", "seed_sprouting"],
            font_pairing={"heading": "Libre Baskerville", "body": "Raleway"},
            mood_keywords=["crecimiento", "flujo", "naturaleza", "abundancia", "vida"],
            background_style="green_growth"
        ),
    ],
    
    EsotericCategory.VENGANZA_SEPARACION: [
        DesignAtmosphere(
            name="Oscuridad Vengadora",
            primary_colors=["#09090B", "#18181B", "#27272A"],
            secondary_colors=["#DC2626", "#B91C1C", "#991B1B"],
            accent_colors=["#7C3AED", "#8B5CF6", "#A78BFA"],
            gradient_styles=[
                "linear-gradient(180deg, #09090B 0%, #18181B 100%)",
                "radial-gradient(circle at bottom, #DC2626, #09090B)"
            ],
            icon_set=["⚡", "🖤", "💔", "🔥", "⛓️", "🌑", "💀"],
            animation_intensity="intense",
            visual_elements=["dark_flames", "breaking_chains", "lightning_strikes", "shadow_tendrils"],
            font_pairing={"heading": "Bebas Neue", "body": "Archivo"},
            mood_keywords=["justicia", "liberación", "poder", "ruptura", "fuerza"],
            background_style="dark_power"
        ),
        DesignAtmosphere(
            name="Corte Definitivo",
            primary_colors=["#3F3F46", "#52525B", "#71717A"],
            secondary_colors=["#1E40AF", "#1D4ED8", "#2563EB"],
            accent_colors=["#DC2626", "#EF4444", "#F87171"],
            gradient_styles=[
                "linear-gradient(to bottom, #09090B 0%, #3F3F46 100%)",
                "linear-gradient(135deg, #1E40AF, #09090B, #DC2626)"
            ],
            icon_set=["✂️", "⚔️", "🔗", "💔", "🌙", "🖤", "⛓️‍💥"],
            animation_intensity="moderate",
            visual_elements=["cutting_motion", "chain_breaking", "fade_separation", "cold_steel"],
            font_pairing={"heading": "Teko", "body": "Barlow"},
            mood_keywords=["separación", "corte", "alejamiento", "fin", "liberación"],
            background_style="cold_steel"
        ),
    ],
    
    EsotericCategory.SALUD_SANACION: [
        DesignAtmosphere(
            name="Sanador Ancestral",
            primary_colors=["#16A34A", "#22C55E", "#4ADE80"],
            secondary_colors=["#92400E", "#A16207", "#CA8A04"],
            accent_colors=["#F8FAFC", "#F1F5F9", "#E2E8F0"],
            gradient_styles=[
                "linear-gradient(to bottom, #14532D 0%, #166534 50%, #22C55E 100%)",
                "radial-gradient(ellipse at center, #22C55E, #14532D)"
            ],
            icon_set=["🌿", "🙏", "💚", "🍃", "✨", "🌱", "🌻"],
            animation_intensity="subtle",
            visual_elements=["healing_hands", "herb_aura", "nature_energy", "gentle_glow"],
            font_pairing={"heading": "Amatic SC", "body": "Cabin"},
            mood_keywords=["sanación", "curación", "naturaleza", "vida", "bienestar"],
            background_style="healing_nature"
        ),
        DesignAtmosphere(
            name="Energía Curativa",
            primary_colors=["#0EA5E9", "#38BDF8", "#7DD3FC"],
            secondary_colors=["#A855F7", "#C084FC", "#D8B4FE"],
            accent_colors=["#F0FDFA", "#CCFBF1", "#99F6E4"],
            gradient_styles=[
                "linear-gradient(180deg, #0C4A6E 0%, #0369A1 50%, #0EA5E9 100%)",
                "radial-gradient(circle at 50% 0%, #38BDF8, #0C4A6E)"
            ],
            icon_set=["💙", "✨", "🌊", "💫", "🔵", "💎", "🙏"],
            animation_intensity="moderate",
            visual_elements=["energy_waves", "chakra_glow", "healing_light", "cosmic_healing"],
            font_pairing={"heading": "Exo 2", "body": "Karla"},
            mood_keywords=["energía", "chakras", "cosmos", "vibración", "armonía"],
            background_style="cosmic_healing"
        ),
    ],
    
    EsotericCategory.ESPIRITISMO: [
        DesignAtmosphere(
            name="Portal Espiritual",
            primary_colors=["#1E1B4B", "#312E81", "#3730A3"],
            secondary_colors=["#A78BFA", "#C4B5FD", "#DDD6FE"],
            accent_colors=["#F8FAFC", "#E0E7FF", "#C7D2FE"],
            gradient_styles=[
                "linear-gradient(180deg, #020617 0%, #0F172A 30%, #1E1B4B 100%)",
                "radial-gradient(ellipse at center, #3730A3, #020617)"
            ],
            icon_set=["👻", "🌌", "💫", "🔮", "👁️", "✨", "🌙"],
            animation_intensity="subtle",
            visual_elements=["ethereal_mist", "spirit_orbs", "dimensional_portal", "ghostly_glow"],
            font_pairing={"heading": "Italiana", "body": "Philosopher"},
            mood_keywords=["espíritus", "más allá", "mensajes", "conexión", "paz"],
            background_style="ethereal_realm"
        ),
    ],
}


# =============================================================================
# MOTOR DE ANÁLISIS DE KEYWORDS
# =============================================================================

class KeywordAnalyzer:
    """Analiza keywords para determinar categoría y tono."""
    
    # Patrones de palabras clave por categoría
    KEYWORD_PATTERNS: Dict[EsotericCategory, List[str]] = {
        EsotericCategory.AMOR_AMARRES: [
            "amarre", "amor", "pareja", "ex", "enamorar", "atraer", "seducir",
            "regrese", "vuelva", "matrimonio", "romance", "corazón", "pasión",
            "amado", "amada", "conquistar", "reconciliación", "endulzamiento",
            "ligamiento", "hechizo de amor", "ritual amor", "unión"
        ],
        EsotericCategory.TAROT_ADIVINACION: [
            "tarot", "cartas", "videncia", "vidente", "lectura", "futuro",
            "predicción", "adivinación", "oráculo", "clarividencia", "horóscopo",
            "astral", "zodíaco", "bola de cristal", "arcanos", "tirada"
        ],
        EsotericCategory.BRUJERIA_MAGIA: [
            "brujo", "bruja", "brujería", "magia", "hechizo", "ritual",
            "conjuro", "embrujo", "aquelarre", "coven", "grimorio",
            "hechicero", "mago", "poción", "encantamiento"
        ],
        EsotericCategory.SANTERIA_VUDÚ: [
            "santería", "santero", "santera", "orishas", "vudú", "voodoo",
            "changó", "yemayá", "oshún", "elegua", "obatalá", "babalawo",
            "ifá", "caracoles", "oráculo yoruba", "religión afro"
        ],
        EsotericCategory.PROTECCION_LIMPIEZA: [
            "protección", "limpieza", "barrida", "despojo", "mal de ojo",
            "envidia", "malas energías", "salación", "brujería contra",
            "amuleto", "talismán", "escudo", "defensa", "purificación"
        ],
        EsotericCategory.PROSPERIDAD_DINERO: [
            "dinero", "prosperidad", "abundancia", "negocio", "trabajo",
            "fortuna", "riqueza", "éxito", "suerte", "lotería", "finanzas",
            "economía", "deudas", "empleo", "empresa"
        ],
        EsotericCategory.VENGANZA_SEPARACION: [
            "separación", "separar", "alejar", "venganza", "justicia",
            "romper", "destruir", "castigar", "enemigo", "rival",
            "tercera persona", "amante", "infidelidad", "divorcio"
        ],
        EsotericCategory.SALUD_SANACION: [
            "curandero", "curandera", "sanación", "salud", "enfermedad",
            "curación", "medicina tradicional", "hierbas", "chamán",
            "ancestral", "remedio", "terapia", "bienestar"
        ],
        EsotericCategory.ESPIRITISMO: [
            "espiritismo", "médium", "espíritu", "alma", "difunto",
            "mensaje espiritual", "canalización", "sesión", "más allá",
            "contacto espiritual", "fantasma", "presencia"
        ],
    }
    
    # Modificadores de intensidad
    INTENSITY_MODIFIERS = {
        "urgente": 1.5,
        "poderoso": 1.4,
        "fuerte": 1.3,
        "efectivo": 1.2,
        "garantizado": 1.3,
        "rápido": 1.2,
        "inmediato": 1.4,
        "definitivo": 1.3,
        "extremo": 1.5,
        "potente": 1.4,
    }
    
    @classmethod
    def analyze(cls, keywords: List[str]) -> Tuple[EsotericCategory, float, List[str]]:
        """
        Analiza una lista de keywords y determina:
        - Categoría principal
        - Nivel de intensidad (0.0 a 1.0)
        - Keywords más relevantes
        
        Returns:
            Tuple[EsotericCategory, float, List[str]]
        """
        # Unir y normalizar keywords
        all_text = " ".join(keywords).lower()
        
        # Calcular puntuación por categoría
        category_scores: Dict[EsotericCategory, float] = {}
        matched_keywords: Dict[EsotericCategory, List[str]] = {}
        
        for category, patterns in cls.KEYWORD_PATTERNS.items():
            score = 0.0
            matches = []
            
            for pattern in patterns:
                if pattern.lower() in all_text:
                    score += 1.0
                    matches.append(pattern)
                    
                    # Bonus por coincidencia exacta
                    for kw in keywords:
                        if pattern.lower() == kw.lower():
                            score += 0.5
            
            category_scores[category] = score
            matched_keywords[category] = matches
        
        # Determinar categoría ganadora
        if not any(category_scores.values()):
            # Default a BRUJERIA_MAGIA si no hay coincidencias
            best_category = EsotericCategory.BRUJERIA_MAGIA
        else:
            best_category = max(category_scores, key=category_scores.get)
        
        # Calcular intensidad basada en modificadores
        intensity = 0.5  # Base
        for modifier, boost in cls.INTENSITY_MODIFIERS.items():
            if modifier in all_text:
                intensity = min(1.0, intensity * boost)
        
        return best_category, intensity, matched_keywords.get(best_category, [])


# =============================================================================
# GENERADOR DE DISEÑO DINÁMICO
# =============================================================================

@dataclass
class DesignConfiguration:
    """Configuración completa de diseño generada."""
    
    # Identificación
    design_id: str
    design_name: str
    timestamp: str
    
    # Categoría detectada
    category: EsotericCategory
    category_confidence: float
    matched_keywords: List[str]
    
    # Atmósfera seleccionada
    atmosphere: DesignAtmosphere
    
    # Colores específicos para este diseño
    colors: Dict[str, str]
    
    # Gradientes a usar
    gradients: Dict[str, str]
    
    # Fuentes
    fonts: Dict[str, str]
    font_import_url: str
    
    # Animaciones CSS personalizadas
    animations: Dict[str, str]
    
    # Elementos visuales activos
    visual_elements: List[str]
    
    # Iconografía
    icons: List[str]
    hero_icon: str
    
    # CSS Variables generadas
    css_variables: str
    
    # CSS de animaciones
    animation_css: str
    
    # Estilos inline para secciones
    section_styles: Dict[str, str]
    
    # Meta info para SEO
    design_meta: Dict[str, str]


class DesignGenerator:
    """Genera diseños únicos basados en análisis de keywords."""
    
    # Historial para evitar repetición (en producción usar Redis/DB)
    _design_history: List[str] = []
    _max_history = 50
    
    # Animaciones CSS por intensidad
    ANIMATIONS = {
        "subtle": {
            "float": """
                @keyframes float {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(-8px); }
                }
            """,
            "pulse-soft": """
                @keyframes pulse-soft {
                    0%, 100% { opacity: 0.8; }
                    50% { opacity: 1; }
                }
            """,
            "fade-in": """
                @keyframes fade-in {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            """,
        },
        "moderate": {
            "float": """
                @keyframes float {
                    0%, 100% { transform: translateY(0) rotate(0deg); }
                    50% { transform: translateY(-15px) rotate(2deg); }
                }
            """,
            "glow": """
                @keyframes glow {
                    0%, 100% { box-shadow: 0 0 20px var(--glow-color, rgba(168, 85, 247, 0.4)); }
                    50% { box-shadow: 0 0 40px var(--glow-color, rgba(168, 85, 247, 0.7)); }
                }
            """,
            "shimmer": """
                @keyframes shimmer {
                    0% { background-position: -200% 0; }
                    100% { background-position: 200% 0; }
                }
            """,
            "pulse-glow": """
                @keyframes pulse-glow {
                    0%, 100% { opacity: 0.7; transform: scale(1); }
                    50% { opacity: 1; transform: scale(1.05); }
                }
            """,
        },
        "intense": {
            "float-intense": """
                @keyframes float-intense {
                    0%, 100% { transform: translateY(0) scale(1); }
                    25% { transform: translateY(-20px) scale(1.02); }
                    50% { transform: translateY(-10px) scale(1); }
                    75% { transform: translateY(-25px) scale(1.03); }
                }
            """,
            "fire-flicker": """
                @keyframes fire-flicker {
                    0%, 100% { opacity: 1; transform: scale(1) rotate(-1deg); }
                    25% { opacity: 0.9; transform: scale(1.02) rotate(1deg); }
                    50% { opacity: 1; transform: scale(0.98) rotate(-2deg); }
                    75% { opacity: 0.95; transform: scale(1.01) rotate(2deg); }
                }
            """,
            "energy-pulse": """
                @keyframes energy-pulse {
                    0% { box-shadow: 0 0 0 0 var(--pulse-color, rgba(220, 38, 38, 0.7)); }
                    70% { box-shadow: 0 0 0 20px var(--pulse-color, rgba(220, 38, 38, 0)); }
                    100% { box-shadow: 0 0 0 0 var(--pulse-color, rgba(220, 38, 38, 0)); }
                }
            """,
            "shake-subtle": """
                @keyframes shake-subtle {
                    0%, 100% { transform: translateX(0); }
                    25% { transform: translateX(-2px); }
                    75% { transform: translateX(2px); }
                }
            """,
        },
    }
    
    # Efectos visuales CSS
    VISUAL_EFFECTS = {
        "hearts_floating": """
            .floating-hearts::before {
                content: '❤️ 💕 💖';
                position: absolute;
                font-size: 2rem;
                animation: float 4s ease-in-out infinite;
                opacity: 0.3;
            }
        """,
        "candle_flames": """
            .candle-effect {
                background: linear-gradient(to top, #FF6B35 0%, #F7931A 50%, transparent 100%);
                border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
                animation: fire-flicker 0.5s ease-in-out infinite alternate;
            }
        """,
        "crystal_ball_glow": """
            .crystal-glow {
                background: radial-gradient(circle at 30% 30%, rgba(168, 85, 247, 0.3), transparent);
                box-shadow: 0 0 60px rgba(168, 85, 247, 0.4), inset 0 0 60px rgba(168, 85, 247, 0.1);
                animation: glow 3s ease-in-out infinite;
            }
        """,
        "mystic_smoke": """
            .mystic-smoke {
                background: linear-gradient(to top, transparent, rgba(168, 85, 247, 0.1));
                filter: blur(20px);
                animation: float 8s ease-in-out infinite;
            }
        """,
        "gold_coins_falling": """
            .gold-rain::after {
                content: '💰 💵 ✨';
                position: absolute;
                font-size: 1.5rem;
                animation: float 3s linear infinite;
                opacity: 0.5;
            }
        """,
        "energy_waves": """
            .energy-waves {
                background: 
                    radial-gradient(circle, transparent 20%, rgba(14, 165, 233, 0.1) 40%, transparent 60%),
                    radial-gradient(circle, transparent 30%, rgba(168, 85, 247, 0.1) 50%, transparent 70%);
                animation: pulse-glow 4s ease-in-out infinite;
            }
        """,
        "dark_flames": """
            .dark-fire {
                background: linear-gradient(to top, #DC2626 0%, #991B1B 30%, #09090B 70%);
                animation: fire-flicker 0.3s ease-in-out infinite alternate;
            }
        """,
        "stars_twinkling": """
            .stars::before,
            .stars::after {
                content: '✨ ⭐ 🌟';
                position: absolute;
                font-size: 0.8rem;
                animation: pulse-soft 2s ease-in-out infinite;
                opacity: 0.6;
            }
        """,
    }
    
    @classmethod
    def generate(cls, keywords: List[str], customer_id: str = "") -> DesignConfiguration:
        """
        Genera una configuración de diseño única basada en keywords.
        
        Args:
            keywords: Lista de palabras clave del grupo de anuncios
            customer_id: ID del cliente para personalización
            
        Returns:
            DesignConfiguration con todos los estilos
        """
        # Análisis de keywords
        category, intensity, matched = KeywordAnalyzer.analyze(keywords)
        
        logger.info(f"🎨 Categoría detectada: {category.value} (confianza: {intensity:.2f})")
        logger.info(f"📝 Keywords coincidentes: {matched}")
        
        # Obtener atmósferas disponibles para esta categoría
        available_atmospheres = ATMOSPHERES.get(category, ATMOSPHERES[EsotericCategory.BRUJERIA_MAGIA])
        
        # Seleccionar atmósfera evitando repetición
        atmosphere = cls._select_unique_atmosphere(available_atmospheres, customer_id)
        
        logger.info(f"✨ Atmósfera seleccionada: {atmosphere.name}")
        
        # Generar ID único
        design_id = cls._generate_design_id(atmosphere.name, keywords)
        
        # Seleccionar colores (variación dentro de la paleta)
        colors = cls._generate_color_scheme(atmosphere)
        
        # Generar gradientes
        gradients = cls._generate_gradients(atmosphere, colors)
        
        # Configurar fuentes
        fonts = atmosphere.font_pairing
        font_import_url = cls._generate_font_import_url(fonts)
        
        # Seleccionar animaciones según intensidad
        animations = cls.ANIMATIONS.get(atmosphere.animation_intensity, cls.ANIMATIONS["moderate"])
        
        # Seleccionar iconos (randomizado)
        icons = random.sample(atmosphere.icon_set, min(5, len(atmosphere.icon_set)))
        hero_icon = random.choice(atmosphere.icon_set)
        
        # Generar CSS variables
        css_variables = cls._generate_css_variables(colors, atmosphere)
        
        # Generar CSS de animaciones
        animation_css = cls._generate_animation_css(atmosphere, animations)
        
        # Generar estilos de sección
        section_styles = cls._generate_section_styles(atmosphere, colors, gradients)
        
        # Meta información
        design_meta = {
            "theme": atmosphere.name,
            "mood": ", ".join(atmosphere.mood_keywords[:3]),
            "style": atmosphere.background_style,
        }
        
        return DesignConfiguration(
            design_id=design_id,
            design_name=atmosphere.name,
            timestamp=datetime.now().isoformat(),
            category=category,
            category_confidence=intensity,
            matched_keywords=matched,
            atmosphere=atmosphere,
            colors=colors,
            gradients=gradients,
            fonts=fonts,
            font_import_url=font_import_url,
            animations=animations,
            visual_elements=atmosphere.visual_elements,
            icons=icons,
            hero_icon=hero_icon,
            css_variables=css_variables,
            animation_css=animation_css,
            section_styles=section_styles,
            design_meta=design_meta,
        )
    
    @classmethod
    def _select_unique_atmosphere(cls, atmospheres: List[DesignAtmosphere], customer_id: str) -> DesignAtmosphere:
        """Selecciona una atmósfera evitando repeticiones recientes."""
        # Crear lista de candidatos
        candidates = [a for a in atmospheres if a.name not in cls._design_history[-10:]]
        
        if not candidates:
            # Si todos fueron usados recientemente, limpiar historial
            cls._design_history = cls._design_history[-5:]
            candidates = atmospheres
        
        # Selección pseudoaleatoria basada en hora y customer
        seed = hash(f"{customer_id}_{datetime.now().strftime('%Y%m%d%H')}")
        random.seed(seed)
        selected = random.choice(candidates)
        random.seed()  # Reset seed
        
        # Registrar en historial
        cls._design_history.append(selected.name)
        if len(cls._design_history) > cls._max_history:
            cls._design_history = cls._design_history[-cls._max_history:]
        
        return selected
    
    @classmethod
    def _generate_design_id(cls, atmosphere_name: str, keywords: List[str]) -> str:
        """Genera un ID único para el diseño."""
        content = f"{atmosphere_name}_{','.join(keywords)}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    @classmethod
    def _generate_color_scheme(cls, atmosphere: DesignAtmosphere) -> Dict[str, str]:
        """Genera un esquema de colores con ligera variación."""
        primary = random.choice(atmosphere.primary_colors)
        secondary = random.choice(atmosphere.secondary_colors)
        accent = random.choice(atmosphere.accent_colors)
        
        # 🛡️ COLORES ULTRA-BRILLANTES GARANTIZADOS PARA GRADIENTES DE TEXTO
        # Estos colores SIEMPRE serán visibles en fondos oscuros
        GRADIENT_SAFE_COLORS = {
            "start": "#E879F9",   # Fuchsia 400 - MUY brillante
            "mid": "#FBBF24",     # Amber 400 - Dorado vibrante
            "end": "#34D399",     # Emerald 400 - Verde brillante
        }
        
        # Asegurar que primary_light sea SIEMPRE claro para gradientes de texto
        primary_light = cls._ensure_light_color(atmosphere.primary_colors[0])
        
        # Colores seguros para gradiente basados en la atmósfera pero garantizados brillantes
        gradient_start = cls._ensure_light_color(atmosphere.primary_colors[0])
        gradient_mid = cls._ensure_light_color(secondary)
        gradient_end = cls._ensure_light_color(accent)
        
        return {
            "primary": primary,
            "secondary": secondary,
            "accent": accent,
            "primary_dark": atmosphere.primary_colors[-1],
            "primary_light": primary_light,
            "text": "#F8FAFC",  # Blanco casi puro
            "text_muted": "#CBD5E1",  # Gris claro (más legible)
            "text_heading": "#FFFFFF",  # Blanco puro para títulos
            # 🛡️ Colores GARANTIZADOS brillantes para gradientes de texto
            "gradient_text_start": gradient_start,
            "gradient_text_mid": gradient_mid,
            "gradient_text_end": gradient_end,
            "surface": "#1E293B",
            "background": "#0F172A",
        }
    
    @classmethod
    def _ensure_light_color(cls, color: str) -> str:
        """
        Asegura que un color sea lo suficientemente claro para ser visible en fondos oscuros.
        Si el color es muy oscuro, lo aclara.
        """
        # Colores ULTRA BRILLANTES predefinidos como fallback - GARANTIZADOS visibles
        ULTRA_BRIGHT_COLORS = [
            "#F472B6",  # Pink 400
            "#A78BFA",  # Violet 400
            "#60A5FA",  # Blue 400
            "#34D399",  # Emerald 400
            "#FBBF24",  # Amber 400
            "#FB923C",  # Orange 400
            "#F87171",  # Red 400
            "#E879F9",  # Fuchsia 400
            "#2DD4BF",  # Teal 400
            "#A3E635",  # Lime 400
        ]
        
        try:
            # Convertir hex a RGB
            hex_color = color.lstrip('#')
            if len(hex_color) != 6:
                return random.choice(ULTRA_BRIGHT_COLORS)
                
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            # Calcular luminosidad (fórmula estándar)
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            
            # UMBRAL MÁS ALTO: Si la luminosidad es < 0.55, usar color brillante
            if luminance < 0.55:
                return random.choice(ULTRA_BRIGHT_COLORS)
            return color
        except Exception:
            # Si hay cualquier error, devolver un color brillante seguro
            return random.choice(ULTRA_BRIGHT_COLORS)
    
    @classmethod
    def _generate_gradients(cls, atmosphere: DesignAtmosphere, colors: Dict[str, str]) -> Dict[str, str]:
        """Genera gradientes personalizados."""
        base_gradient = random.choice(atmosphere.gradient_styles)
        
        return {
            "hero": base_gradient,
            "button": f"linear-gradient(135deg, {colors['primary']} 0%, {colors['primary_dark']} 100%)",
            "card": f"linear-gradient(180deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)",
            "cta": f"linear-gradient(90deg, {colors['primary']} 0%, {colors['secondary']} 100%)",
            "overlay": f"linear-gradient(to bottom, transparent 0%, rgba(15, 23, 42, 0.8) 100%)",
        }
    
    @classmethod
    def _generate_font_import_url(cls, fonts: Dict[str, str]) -> str:
        """Genera URL de Google Fonts."""
        heading = fonts.get("heading", "Cinzel").replace(" ", "+")
        body = fonts.get("body", "Outfit").replace(" ", "+")
        
        return f"https://fonts.googleapis.com/css2?family={heading}:wght@400;500;600;700&family={body}:wght@300;400;500;600;700&display=swap"
    
    @classmethod
    def _generate_css_variables(cls, colors: Dict[str, str], atmosphere: DesignAtmosphere) -> str:
        """Genera CSS custom properties."""
        # Colores de gradiente garantizados brillantes
        gradient_start = colors.get('gradient_text_start', '#E879F9')
        gradient_mid = colors.get('gradient_text_mid', '#FBBF24')
        gradient_end = colors.get('gradient_text_end', '#34D399')
        
        return f"""
        :root {{
            /* Colores base */
            --color-primary: {colors['primary']};
            --color-secondary: {colors['secondary']};
            --color-accent: {colors['accent']};
            --color-primary-dark: {colors['primary_dark']};
            --color-primary-light: {colors['primary_light']};
            
            /* Colores de texto - SIEMPRE claros */
            --color-text: {colors['text']};
            --color-text-heading: {colors.get('text_heading', '#FFFFFF')};
            --color-text-muted: {colors['text_muted']};
            
            /* Superficies */
            --color-surface: {colors['surface']};
            --color-background: {colors['background']};
            
            /* Efectos */
            --glow-color: {colors['primary']}66;
            --pulse-color: {colors['accent']}99;
            
            /* 🛡️ GRADIENTE DE TEXTO SEGURO - Colores ultra-brillantes garantizados */
            --gradient-text-start: {gradient_start};
            --gradient-text-mid: {gradient_mid};
            --gradient-text-end: {gradient_end};
            --gradient-text-fallback: #FFFFFF;
            
            /* Fuentes */
            --font-heading: '{atmosphere.font_pairing.get("heading", "Cinzel")}', serif;
            --font-body: '{atmosphere.font_pairing.get("body", "Outfit")}', sans-serif;
            
            /* Animaciones */
            --animation-intensity: {1.0 if atmosphere.animation_intensity == "intense" else 0.7 if atmosphere.animation_intensity == "moderate" else 0.4};
        }}
        
        /* 🛡️ REGLAS DE SEGURIDAD DE CONTRASTE INYECTADAS DESDE BACKEND */
        
        /* Títulos siempre visibles */
        h1, h2, h3, h4, h5, h6 {{
            color: var(--color-text-heading, #FFFFFF) !important;
        }}
        
        /* Gradientes de texto con colores BRILLANTES forzados */
        .bg-clip-text.text-transparent,
        [class*="bg-gradient"][class*="bg-clip-text"] {{
            background-image: linear-gradient(
                to right,
                var(--gradient-text-start, #E879F9),
                var(--gradient-text-mid, #FBBF24),
                var(--gradient-text-end, #34D399)
            ) !important;
            -webkit-background-clip: text !important;
            background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            /* Sombra de respaldo para máxima visibilidad */
            text-shadow: 0 0 40px var(--gradient-text-start);
        }}
        
        /* Párrafos siempre legibles */
        p, span, li {{
            color: var(--color-text, #E2E8F0);
        }}
        """
    
    @classmethod
    def _generate_animation_css(cls, atmosphere: DesignAtmosphere, animations: Dict[str, str]) -> str:
        """Genera CSS de animaciones."""
        css = "\n".join(animations.values())
        
        # Agregar efectos visuales específicos
        for element in atmosphere.visual_elements:
            if element in cls.VISUAL_EFFECTS:
                css += "\n" + cls.VISUAL_EFFECTS[element]
        
        return css
    
    @classmethod
    def _generate_section_styles(cls, atmosphere: DesignAtmosphere, colors: Dict[str, str], gradients: Dict[str, str]) -> Dict[str, str]:
        """Genera estilos para diferentes secciones."""
        return {
            "hero": f"""
                background: {gradients['hero']};
                position: relative;
                overflow: hidden;
            """,
            "hero_overlay": f"""
                background: linear-gradient(to bottom, transparent 0%, rgba(15, 23, 42, 0.9) 100%);
                position: absolute;
                inset: 0;
            """,
            "content": f"""
                background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.9) 100%);
            """,
            "testimonial": f"""
                background: linear-gradient(135deg, {colors['surface']}ee 0%, {colors['background']}ee 100%);
                border: 1px solid {colors['primary']}33;
            """,
            "cta_button": f"""
                background: {gradients['cta']};
                box-shadow: 0 4px 20px {colors['primary']}44;
                transition: all 0.3s ease;
            """,
            "cta_button_hover": f"""
                transform: translateY(-2px);
                box-shadow: 0 8px 30px {colors['primary']}66;
            """,
            "footer": f"""
                background: {colors['background']};
                border-top: 1px solid {colors['primary']}22;
            """,
        }
    
    @classmethod
    def _generate_layout_config(cls, atmosphere: DesignAtmosphere, forced_style: str = "auto") -> Dict[str, str]:
        """
        Genera configuración de layout estructural.
        Esto permite que la landing tenga estructuras variadas como Elementor.
        """
        # Hero Layouts
        hero_layouts = [
            "centered",       # Clásico centrado
            "split_left",     # Texto izquierda, imagen/icono derecha
            "split_right",    # Texto derecha, imagen/icono izquierda
            "overlay_card",   # Texto en tarjeta flotante sobre fondo
            "minimal"         # Texto grande, minimalista
        ]
        
        # Features/Benefits Layouts
        feature_layouts = [
            "grid_3",         # Grid de 3 columnas
            "grid_2",         # Grid de 2 columnas
            "zigzag",         # Lista alternada imagen/texto
            "cards"           # Tarjetas con efecto flotante
        ]
        
        # Content Layouts
        content_layouts = [
            "single_column",  # Columna central estrecha (lectura)
            "split_image_text", # Bloques anchos con fondo alternado
            "single_column"   # Fallback for magazine style
        ]
        
        # Seleccionar layout
        hero_choice = "centered"
        
        if forced_style != "auto" and forced_style:
            # Mapeo de estilos forzados
            if forced_style == "modern":
                hero_choice = random.choice(["split_left", "split_right"])
            elif forced_style == "impact":
                hero_choice = "overlay_card"
            elif forced_style == "classic":
                hero_choice = "centered"
            elif forced_style == "minimal":
                hero_choice = "minimal"
            else:
                hero_choice = random.choice(hero_layouts)
        else:
            # Lógica automática basada en atmósfera
            if atmosphere.animation_intensity == "intense":
                # Para atmósferas intensas, preferir layouts dramáticos
                hero_choice = random.choice(["overlay_card", "centered", "split_left"])
            elif atmosphere.animation_intensity == "subtle":
                # Para atmósferas sutiles, preferir minimalismo
                hero_choice = random.choice(["minimal", "centered", "split_right"])
            else:
                hero_choice = random.choice(hero_layouts)
            
        return {
            "hero_style": hero_choice,
            "features_style": random.choice(feature_layouts),
            "content_style": random.choice(content_layouts),
            "border_radius": random.choice(["0px", "8px", "16px", "24px", "9999px"])
        }


# =============================================================================
# FUNCIÓN PRINCIPAL DE INTEGRACIÓN
# =============================================================================

def generate_dynamic_design(keywords: List[str], customer_id: str = "", layout_style: str = "auto") -> Dict[str, Any]:
    """
    Función principal para generar diseño dinámico.
    
    Args:
        keywords: Lista de keywords del grupo de anuncios
        customer_id: ID del cliente
        layout_style: Estilo de layout forzado (auto, modern, impact, classic, minimal)
        
    Returns:
        Diccionario con toda la configuración de diseño
    """
    config = DesignGenerator.generate(keywords, customer_id)
    
    # Generar layout estructural
    layout_config = DesignGenerator._generate_layout_config(config.atmosphere, forced_style=layout_style)
    
    # Append border radius to CSS variables
    css_variables = config.css_variables + f"\n        :root {{ --border-radius: {layout_config['border_radius']}; }}"
    
    return {
        "design_id": config.design_id,
        "design_name": config.design_name,
        "category": config.category.value,
        "category_confidence": config.category_confidence,
        "matched_keywords": config.matched_keywords,
        "atmosphere_name": config.atmosphere.name,
        
        # Colores
        "colors": config.colors,
        "gradients": config.gradients,
        
        # Tipografía
        "fonts": config.fonts,
        "font_import_url": config.font_import_url,
        
        # Animaciones
        "animation_intensity": config.atmosphere.animation_intensity,
        "css_variables": css_variables,
        "animation_css": config.animation_css,
        
        # Elementos visuales
        "visual_elements": config.visual_elements,
        "icons": config.icons,
        "hero_icon": config.hero_icon,
        
        # Estilos de sección
        "section_styles": config.section_styles,
        
        # Layout Estructural (Nuevo para nivel Elementor)
        "layout": layout_config,
        
        # Meta
        "design_meta": config.design_meta,
        "mood_keywords": config.atmosphere.mood_keywords,
        "timestamp": config.timestamp,
    }


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    # Test con diferentes keywords
    test_cases = [
        ["amarre de amor", "recuperar ex", "hechizo poderoso"],
        ["tarot", "lectura cartas", "vidente"],
        ["brujo", "ritual", "magia negra"],
        ["santería", "orishas", "yemayá"],
        ["limpieza espiritual", "protección", "mal de ojo"],
        ["dinero", "prosperidad", "negocio"],
        ["separación", "alejar persona", "venganza"],
        ["curandero", "sanación", "hierbas"],
    ]
    
    print("=" * 80)
    print("🔮 TEST DEL SISTEMA DE INTELIGENCIA DE DISEÑO")
    print("=" * 80)
    
    for keywords in test_cases:
        print(f"\n📝 Keywords: {keywords}")
        design = generate_dynamic_design(keywords, "test_customer")
        print(f"   🎨 Categoría: {design['category']}")
        print(f"   ✨ Atmósfera: {design['atmosphere_name']}")
        print(f"   🎯 Confianza: {design['category_confidence']:.2f}")
        print(f"   🌈 Color primario: {design['colors']['primary']}")
        print(f"   💫 Icono hero: {design['hero_icon']}")
        print(f"   🎭 Mood: {', '.join(design['mood_keywords'][:3])}")
