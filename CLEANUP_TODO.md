# Truck Rental Platform - Cleanup & Standardization TODO

## ✅ COMPLETED CLEANUP ACTIONS

### Files Removed
- ❌ `quotations/route_models.py` - DELETED (exact duplicate of models in quotations/models.py)
- ❌ `quotations/models_new.py` - DELETED (empty file)

### Model Issues Fixed
- ✅ **Quotation Model**: Fixed duplicate fields and removed invalid save() method
  - Removed duplicate status, is_active, created_at, updated_at fields
  - Removed save() method that referenced non-existent fields (total_base_price, etc.)
  - Consolidated class Meta definitions

### New Centralized Files Created
- ✅ **`project/permissions.py`** - Centralized permission classes to avoid duplication

### Permission Migration Completed ✅
- ✅ **`trucks/api/views.py`** - Replaced local IsVendor, IsVendorOrReadOnly with centralized imports
- ✅ **`orders/api/views.py`** - Replaced local IsCustomer, IsVendor, IsCustomerOrVendor with centralized imports
- ✅ **`payments/api/views.py`** - Replaced local IsCustomer, IsVendor, IsCustomerOrVendor with centralized imports  
- ✅ **`quotations/helper.py`** - Replaced local permission classes with centralized imports

### Permission System Improvements
- ✅ **Enhanced IsVendorOrReadOnly**: Added object-level permissions for vendor ownership validation
- ✅ **All imports validated**: Tested compilation and imports for all modified files

## 🔄 PENDING CLEANUP ACTIONS

### ~~1. Update Permission Imports~~ ✅ COMPLETED
~~Replace scattered permission classes with centralized ones:~~

**~~Files to Update:~~** ✅ ALL COMPLETED
- ~~`trucks/api/views.py` - Replace local IsVendor, IsVendorOrReadOnly with imports from project.permissions~~
- ~~`orders/api/views.py` - Replace local IsCustomer, IsVendor, IsCustomerOrVendor~~
- ~~`payments/api/views.py` - Replace local IsCustomer, IsVendor, IsCustomerOrVendor~~
- ~~`quotations/helper.py` - Replace with imports from project.permissions~~

**Example Replace Pattern:**
```python
# OLD
class IsVendor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'vendor'

# NEW
from project.permissions import IsVendor
```

### 1. Model Field Standardization

**CustomerEnquiry Model** - Standardize location field defaults:
- All location fields should have consistent default behavior
- Consider whether default=0.0 is appropriate or if null=True, blank=True is better

**RoutePricing Model** - Add missing validation:
- Add validation for segment_distance_km using haversine formula
- Ensure price calculations are consistent

### 2. URL Pattern Standardization
- Ensure all URL patterns use trailing slashes consistently
- Review API endpoint naming conventions

### 3. Documentation Updates
- Update API_DOCUMENTATION.md to reflect model changes
- Remove references to deleted route_models.py

## 🏗️ ARCHITECTURAL IMPROVEMENTS

### 1. Create Base Model Classes
Consider creating base models for common patterns:
```python
class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class LocationModel(models.Model):
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    address = models.TextField(blank=True)
    
    class Meta:
        abstract = True
```

### 2. Enhanced Validation
- Add model validation for pincode format using location_utils.validate_pincode()
- Add coordinate validation for latitude/longitude ranges
- Add business logic validation (e.g., pickup_date < delivery_date)

### 3. Signal Integration
Consider adding Django signals for:
- Auto-calculating distances when coordinates are saved
- Auto-generating order numbers, payment IDs, invoice numbers
- Updating truck availability when assigned to orders

## 🧪 TESTING IMPROVEMENTS

### 1. Model Tests
- Add comprehensive model tests for all constraints
- Test auto-generation of IDs and numbers
- Test cascade behaviors and unique constraints

### 2. API Tests
- Add tests for standardized response format
- Test permission classes with all role combinations
- Integration tests for complex workflows (enquiry → quote → order)

## 🔧 DEVELOPMENT TOOLS

### 1. Management Commands to Add
- `python manage.py check_model_consistency` - Validate model relationships
- `python manage.py cleanup_duplicates` - Find and report duplicate data
- `python manage.py validate_locations` - Check coordinate/pincode consistency

### 2. Admin Interface Improvements
- Add proper admin interfaces for all models
- Include filters and search fields for better management
- Add readonly fields for auto-generated values

## 📊 MONITORING & LOGGING

### 1. Add Logging
- Log permission denials for security monitoring
- Log price calculations for audit trails
- Log location service calls for performance monitoring

### 2. Performance Optimization
- Add database indexes for frequently queried fields
- Consider caching for pincode-to-coordinates mapping
- Optimize route search algorithm for large datasets

---

## Priority Order for Implementation

1. ~~**HIGH PRIORITY** - Update permission imports (affects security)~~ ✅ COMPLETED
2. **MEDIUM PRIORITY** - Standardize model fields (affects data consistency)  
3. **LOW PRIORITY** - Architectural improvements (affects maintainability)

## Validation Commands

After implementing changes, run:
```bash
python manage.py makemigrations --dry-run  # Check for migration issues
python manage.py check                     # Check for model issues
python manage.py test                      # Run test suite
python manage.py create_sample_data --clear  # Verify sample data creation
```
