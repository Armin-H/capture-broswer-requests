
from pydantic import BaseModel, Field
from typing import List, Optional
import instructor
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

class TechItem(BaseModel):
    name: str = Field(description="The canonical name of the tool, language, or platform. e.g., 'AWS S3', 'dbt'")

class TechnicalSkill(BaseModel):
    name: str = Field(description="The engineering methodology or practice. e.g., 'Data modeling', 'CI/CD', 'Unit testing'")

class SoftSkill(BaseModel):
    desc: str = Field(description="Interpersonal trait or working style. e.g., 'Stakeholder communication', 'Thriving in ambiguity'")

class CloudService(BaseModel):
    cloud_provider : str = Field(description="The cloud provider. e.g., 'AWS', 'Azure', 'GCP', ...")
    cloud_service : str = Field(description="The cloud service. e.g., 'S3', 'RDS', 'Redshift'")

class ProgrammingLanguage(BaseModel):
    name: str = Field(description="The canonical name of the programming language. e.g., 'Python', 'JavaScript', 'Java'")
    experience: str = Field(description="The experience level of the programming language. e.g., 'Expert', 'Advanced', 'Intermediate', '2 Years'")

class JobProfile(BaseModel):
    global_years_of_experience: Optional[int] = Field(default=None, description="The minimum years of experience required for the role overall.")
    programming_languages: List[ProgrammingLanguage] = Field(default=[])
    tech_stack: List[TechItem] = Field(default=[])
    cloud_services: List[CloudService] = Field(default=[])
    technical_skills: List[TechnicalSkill] = Field(default=[])
    soft_skills: List[SoftSkill] = Field(default=[])
    domain_knowledge: List[str] = Field(default=[], description="Industries or regulations, e.g., 'Fintech', 'GDPR'")
    certifications: List[str] = Field(default=[])
    education: Optional[str] = Field(default=None, description="Highest degree requested, e.g., 'Bachelors in Computer Science'")


class JobAdParser:

    system_prompt = """You are an expert AI recruiter extracting structured fields from job descriptions.

    Fill JobProfile only from what is explicitly stated or clearly implied in the text.
    Do not invent tools, skills, years, certifications, or education.

    Rules:
    - global_years_of_experience: minimum years required for the role overall as an integer; otherwise null.
    - programming_languages: programming languages used in the job description.
    - tech_stack: concrete tools, platforms, databases, orchestrators (e.g. PostgreSQL, Airflow), Don't include programming languages and cloud services in the tech_stack list.
    - cloud_services: cloud services used in the job description(e.g. AWS Glue, Azure Data Factory).
    - technical_skills: engineering practices/methodologies (e.g. data modeling, CI/CD, query optimization), not product names.
    - soft_skills: interpersonal/working-style traits (e.g. stakeholder communication), shortten the description to 2-3 words if it's long.
    - domain_knowledge: industries, business domains, or regulations (e.g. Fintech, trading, GDPR).
    - certifications / education: only if requested; otherwise empty / null.
    - education: highest degree requested(e.g. Bachelor's of Science); otherwise empty / null.
    - Prefer canonical short names. Deduplicate. Leave lists empty when nothing is found.
    """

    def __init__(self, model_name):
        self.model_name = model_name


        OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
        client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        )
        self.instructor_client = instructor.from_openai(client)

    def parse(self, job_desc):


        user_prompt = f"""Extract structured job requirements from the job description below.

        Job description:
        {job_desc}
        """
        print(len(self.system_prompt), len(user_prompt))
        response = self.instructor_client.chat.completions.create(
        model=self.model_name,
        messages=[
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_model=JobProfile,
        temperature = 0.0
        )
        return response