import datetime

class PriorityEngine:
    def __init__(self, weights=None, horizon_days=7):
        """
        Initializes the PriorityEngine with weights for different factors.
        
        :param weights: Dictionary containing weights for 'urgency', 'importance', 
                        'sender_rank', and 'deadline'. Sum of weights should be 1.0.
        :param horizon_days: Time horizon in days used for calculating deadline factor.
        """
        if weights is None:
            self.weights = {
                'urgency': 0.3,
                'importance': 0.3,
                'sender_rank': 0.2,
                'deadline': 0.2
            }
        else:
            self.weights = weights
        
        self.horizon_seconds = horizon_days * 24 * 3600

    def calculate_deadline_factor(self, deadline):
        """
        Calculates a deadline factor between 0.0 and 1.0 based on time remaining.
        
        :param deadline: datetime object or ISO format string.
        :return: float between 0.0 and 1.0.
        """
        if deadline is None:
            return 0.0
        
        if isinstance(deadline, str):
            try:
                # Handle Z suffix for UTC if present
                if deadline.endswith('Z'):
                    deadline = deadline.replace('Z', '+00:00')
                deadline = datetime.datetime.fromisoformat(deadline)
            except ValueError:
                return 0.0
        
        # Ensure we compare timezone-aware or timezone-naive consistently
        if deadline.tzinfo is not None:
            now = datetime.datetime.now(datetime.timezone.utc)
        else:
            now = datetime.datetime.now()
            
        seconds_remaining = (deadline - now).total_seconds()
        
        if seconds_remaining <= 0:
            return 1.0 # Overdue or due now
        
        factor = max(0.0, 1.0 - (seconds_remaining / self.horizon_seconds))
        return factor

    def score(self, urgency, importance, sender_rank, deadline=None):
        """
        Calculate a normalized priority score.
        
        :param urgency: float (0.0 to 1.0)
        :param importance: float (0.0 to 1.0)
        :param sender_rank: float (0.0 to 1.0)
        :param deadline: datetime or ISO string (optional)
        :return: float (0.0 to 1.0)
        """
        deadline_factor = self.calculate_deadline_factor(deadline)
        
        weighted_score = (
            urgency * self.weights.get('urgency', 0) +
            importance * self.weights.get('importance', 0) +
            sender_rank * self.weights.get('sender_rank', 0) +
            deadline_factor * self.weights.get('deadline', 0)
        )
        
        return round(weighted_score, 4)
