from rest_framework.throttling import UserRateThrottle


class ApprovalThrottle(UserRateThrottle):
    scope = 'approval'
    rate = '5/minute'  # Limit to 5 approval/rejection actions per minute
