from apps.worker.celery_app import celery_app

# Periodic jobs land here as their modules ship — e.g. §95 daily_ceo_briefing at 07:30.
# Empty on purpose until a real scheduled task exists (no simulated/fake entries per §202).
celery_app.conf.beat_schedule = {}
