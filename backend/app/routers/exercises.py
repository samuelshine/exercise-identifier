from fastapi import APIRouter

router = APIRouter(prefix="/exercises", tags=["exercises"])


# TODO: implement CRUD endpoints
# GET    /exercises          — list all (paginated)
# GET    /exercises/{id}     — get by ID
# POST   /exercises          — create
# PATCH  /exercises/{id}     — partial update
# DELETE /exercises/{id}     — delete
