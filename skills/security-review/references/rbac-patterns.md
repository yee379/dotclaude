## Ownership Check Pattern

Check on every request — not just at the gateway.

```python
# BAD: assumes gateway enforces auth
async def get_order(order_id: str, db: Session):
    return db.query(Order).filter(Order.id == order_id).first()

# GOOD: enforce ownership in handler
async def get_order(
    order_id: str,
    db: Session,
    current_user: User = Depends(get_current_user),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundError("Order", order_id)
    if order.user_id != current_user.id and current_user.role != Role.ADMIN:
        raise ForbiddenError()
    return order
```

## Role Dependency Pattern

```python
def require_role(*roles: Role):
    def dependency(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise ForbiddenError()
        return current_user
    return dependency

# Usage
@router.delete("/users/{id}")
async def delete_user(
    id: str,
    _: User = Depends(require_role(Role.ADMIN)),
):
    ...
```

## Checklist

- [ ] Every endpoint checks auth (no anonymous access to protected routes)
- [ ] Ownership verified — user can only access their own resources
- [ ] Role checks performed in service layer, not only at gateway
- [ ] GraphQL resolvers enforce auth (not just the HTTP layer)
- [ ] Admin routes protected by role, not just auth
- [ ] IDOR prevented — IDs are opaque or validated
