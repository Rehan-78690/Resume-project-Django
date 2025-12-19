import logging
from .models import AIUsageLog

logger = logging.getLogger(__name__)

class AILogService:
    @staticmethod
    def log_usage(
        user,
        feature_type,
        model_name,
        prompt=None,
        prompt_hash=None,
        tokens_in=0,
        tokens_out=0,
        success=True,
        error_message=""
    ):
        try:
            p_hash = prompt_hash
            if not p_hash and prompt:
                p_hash = str(hash(str(prompt)))
            
            # Simple cost estimation (approximate for GPT-4/3.5)
            # This is a placeholder logic; real logic would depend on model pricing
            cost = 0.0
            if model_name.startswith("gpt-4"):
                cost = (tokens_in * 0.03 + tokens_out * 0.06) / 1000
            elif model_name.startswith("gpt-3.5"):
                cost = (tokens_in * 0.0005 + tokens_out * 0.0015) / 1000
            
            log = AIUsageLog.objects.create(
                user=user,
                feature_type=feature_type,
                model_name=model_name,
                prompt_hash=p_hash or "",
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_estimate=cost,
                success=success,
                error_message=error_message[:1000] if error_message else ""
            )
            return log
        except Exception as e:
            logger.error(f"Failed to log AI usage: {e}")
            return None
