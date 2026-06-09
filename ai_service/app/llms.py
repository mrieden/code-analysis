import os
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from helpers.config import get_settings, Settings
from schemas.characterization import CharacterizationSpec

settings = get_settings()


settings = get_settings()

translator_llm = ChatGroq(
    model= settings.model1,
    api_key=settings.GROQ_API_KEY,
    temperature=0.2,
)

refactor_llm = ChatGroq(
    model= settings.model1,
    api_key=settings.GROQ_API_KEY,
    temperature=0.1,
)

characterize_llm = ChatGroq(
    model= settings.model2,
    api_key=settings.GROQ_API_KEY,
    temperature=0.1,
)


characterize_structured = characterize_llm.with_structured_output(
    CharacterizationSpec, method="json_mode", include_raw=True
)

architect_llm =  ChatGroq(
    model= settings.model1,
    api_key=settings.GROQ_API_KEY,
    temperature=0.2,
)

report_llm = ChatGroq(
	model=settings.model3,          
	api_key=settings.GROQ_API_KEY,
	temperature=0.2,
)

