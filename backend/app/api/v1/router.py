from fastapi import APIRouter

from app.api.v1 import admin_auth, admin_stores, admin_uploads, auth, checkins, history, reviews, states, stores, users


router = APIRouter()
router.include_router(auth.router)
router.include_router(admin_auth.router)
router.include_router(users.router)
router.include_router(stores.router)
router.include_router(checkins.router)
router.include_router(states.favorite_router)
router.include_router(states.eaten_router)
router.include_router(history.router)
router.include_router(reviews.router)
router.include_router(admin_stores.router)
router.include_router(admin_uploads.router)
