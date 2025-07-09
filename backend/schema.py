import strawberry
from typing import List, Optional

user_profiles = []

@strawberry.type
class UserProfile:
    name: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    skills: List[str]
    jobs: Optional[List[str]] = None
    companies: Optional[List[str]] = None
    language: Optional[str] = None  

@strawberry.input
class UserProfileInput:
    name: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    skills: List[str]
    jobs: Optional[List[str]] = None
    companies: Optional[List[str]] = None
    language: Optional[str] = None  # ✅ NEW

@strawberry.type
class Response:
    success: bool
    message: str

@strawberry.type
class Mutation:
    @strawberry.mutation
    def add_user_profile(self, input: UserProfileInput) -> Response:
        profile = UserProfile(
            name=input.name,
            email=input.email,
            phone=input.phone,
            location=input.location,
            skills=input.skills,
            jobs=input.jobs,
            companies=input.companies,
            language=input.language
        )
        user_profiles.append(profile)
        print("Received CV info:", input)
        return Response(success=True, message="User profile saved")

@strawberry.type
class Query:
    @strawberry.field
    def ping(self) -> str:
        return "pong"

    @strawberry.field
    def get_user_profiles(self) -> List[UserProfile]:
        return user_profiles

schema = strawberry.Schema(query=Query, mutation=Mutation)
