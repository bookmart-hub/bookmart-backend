# Bookmart Backend

Here is the comprehensive architectural and database design document for the **Bookmart** marketplace. This design transitions your minimal structure into a highly scalable, decoupled, production-grade Django application layer optimized for Postgres.

---

## 1. Conceptual Design Screen Data Mapping

Based on the 24 user journey flows, the data requirements are split into clear domain layers:

* **Discovery Screens (Home, Search, Recommendations):** Require high-performance read views fetching aggregated `Book` details, calculated spatial geolocations, and dynamic categorization hierarchies.
* **Listing & Request Interaction Screens:** Require split operations: transaction write paths for creating an asset (`Listing`), or recording buyer demand hooks (`BookRequirement`).
* **Contact & Fulfillment Screens:** Require lightweight snapshot data mappings (like your current WhatsApp metadata payload strings) designed to transition into structured transactional chat state hooks later.

---

## 2. Scalable Django App Structure

To prevent a messy monolithic structure as we move from C2C to B2C/B2B, we will isolate components into domain-driven local applications inside an `apps/` directory namespace.

```text
apps/
├── core/                # Shared mixins, abstract timestamp models, custom fields
├── users/               # Custom identity handling, OAuth tokens, Profiles (Consumers vs. Vendors)
├── taxonomy/            # Global tag vectors, categories, authors, structural book metadata
├── inventory/           # C2C individual items, future vendor inventory tables
├── requirements/        # Direct buyer demand matching boards (Wishlists, Requests)
├── locations/           # Spatial indexing engine (Colleges, coordinates, regional scopes)
└── communications/      # Contact abstraction layer (WhatsApp link routers, chat bridges)

```

### Architectural Separations & Justifications

* **Taxonomy vs. Inventory:** Keeping `taxonomy` separate from `inventory` ensures that if five thousand users list a pre-loved copy of *Ikigai*, the core text attributes (ISBN, Authors, Publisher) are defined exactly **once**. This prevents massive duplicate text row indexing overheads.
* **Inventory vs. Requirements:** Separating supply (`inventory`) from buyer demand logs (`requirements`) lets you scale or clean up buyer listings independently without impacting historical sales charts.
* **Locations as an Isolated Infrastructure:** Encapsulating coordinates and institutional boundaries into `locations` prevents you from tightly binding user accounts to specific static schemas. This allows a user to be tied to a college today, while allowing future commercial vendors to map straight to regional warehouse zones.

---

## 3. High-Fidelity Textual ER Diagram

```text
 [users.User] ──(1:1)──> [users.Profile]
      │                        │
      │ (1:N)                  │ (1:N)
      ▼                        ▼
 [inventory.Listing]     [requirements.BookRequirement]
      │                        │
      │ (N:1)                  │ (N:1)
      ▼                        ▼
 [taxonomy.Book] <─────────────┘
      │
      │ (M:N via BookCategory)
      ▼
 [taxonomy.Category]

```

---

## 4. Database Schema & Complete Django Model Layer

We will write clean, explicit Django models using **Django REST Framework** standards, accounting for modern optimization fields.

### A. The Core Application Namespace (`apps/core/models.py`)

```python
from django.db import models

class TimeStampedModel(models.Model):
    """Abstract baseline model to guarantee strict systemic temporal audits."""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

```

### B. The Users Application Namespace (`apps/users/models.py`)

```python
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from apps.core.models import TimeStampedModel

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email boundary missing.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    class AccountType(models.TextChoices):
        CONSUMER = 'CONSUMER', 'Individual Consumer (C2C)'
        VENDOR = 'VENDOR', 'Commercial Merchant (B2C)'
        BUSINESS = 'BUSINESS', 'Enterprise Publisher (B2B)'

    class AuthProvider(models.TextChoices):
        EMAIL = 'EMAIL', 'Standard Email Auth'
        GOOGLE = 'GOOGLE', 'Google OAuth Gateway'
        FACEBOOK = 'FACEBOOK', 'Facebook OAuth Gateway'

    email = models.EmailField(unique=True, db_index=True)
    account_type = models.CharField(max_length=20, choices=AccountType.choices, default=AccountType.CONSUMER)
    auth_provider = models.CharField(max_length=20, choices=AuthProvider.choices, default=AuthProvider.EMAIL)
    provider_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    email_verified = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        indexes = [
            models.Index(fields=['account_type', 'is_active']),
        ]

class Profile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=255)
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True, help_text="Format: +91XXXXXXXXXX")
    
    # Structural links to spatial contexts
    college = models.ForeignKey('locations.College', on_delete=models.SET_Null, null=True, blank=True, related_name='students')
    coordinates = models.ForeignKey('locations.GeoLocation', on_delete=models.SET_Null, null=True, blank=True)

    def __str__(self):
        return f"{self.full_name} ({self.user.account_type})"

```

### C. The Taxonomy Application Namespace (`apps/taxonomy/models.py`)

```python
from django.db import models
from apps.core.models import TimeStampedModel

class Category(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Book(TimeStampedModel):
    isbn_13 = models.CharField(max_length=13, unique=True, db_index=True)
    title = models.CharField(max_length=255, db_index=True)
    authors = models.JSONField(default=list, help_text="Array string structures storing names.")
    publisher = models.CharField(max_length=255, blank=True)
    cover_image_url = models.URLField(blank=True, null=True)
    categories = models.ManyToManyField(Category, related_name='books')

    def __str__(self):
        return self.title

```

### D. The Inventory Application Namespace (`apps/inventory/models.py`)

```python
from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel

class Listing(TimeStampedModel):
    class BookCondition(models.TextChoices):
        NEW = 'NEW', 'Brand New'
        LIKE_NEW = 'LIKE_NEW', 'Like New'
        GOOD = 'GOOD', 'Good'
        ACCEPTABLE = 'ACCEPTABLE', 'Acceptable'

    class ListingStatus(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        PENDING = 'PENDING', 'Pending Transaction'
        SOLD = 'SOLD', 'Sold out'
        ARCHIVED = 'ARCHIVED', 'Deactivated'

    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='listings')
    book = models.ForeignKey('taxonomy.Book', on_delete=models.PROTECT, related_name='listings')
    
    price = models.DecimalField(max_digits=10, decimal_places=2)
    condition = models.CharField(max_length=20, choices=BookCondition.choices, default=BookCondition.GOOD)
    condition_notes = models.TextField(blank=True)
    images = models.JSONField(default=list, help_text="Cloud array endpoints vectors.")
    
    status = models.CharField(max_length=20, choices=ListingStatus.choices, default=ListingStatus.AVAILABLE)
    
    # Location overrides (If seller lists an item outside their home college environment)
    specific_college = models.ForeignKey('locations.College', on_delete=models.SET_Null, null=True, blank=True)
    specific_location = models.ForeignKey('locations.GeoLocation', on_delete=models.SET_Null, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['condition']),
        ]

```

### E. The Requirements Application Namespace (`apps/requirements/models.py`)

```python
from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel

class BookRequirement(TimeStampedModel):
    class RequirementStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Seeking Copy'
        FULFILLED = 'FULFILLED', 'Acquired'
        EXPIRED = 'EXPIRED', 'Closed'

    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='requirements')
    
    # Support both structural references OR raw text if book doesn't exist in system yet
    book = models.ForeignKey('taxonomy.Book', on_delete=models.SET_Null, null=True, blank=True, related_name='demands')
    raw_title = models.CharField(max_length=255, blank=True, null=True, help_text="Fallbacks when ISBN isn't resolved yet.")
    raw_author = models.CharField(max_length=255, blank=True, null=True)
    
    max_acceptable_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=RequirementStatus.choices, default=RequirementStatus.ACTIVE)

    class Meta:
        indexes = [
            models.Index(fields=['status', '-created_at']),
        ]

```

### F. The Locations Application Namespace (`apps/locations/models.py`)

```python
from django.db import models
from apps.core.models import TimeStampedModel

class GeoLocation(TimeStampedModel):
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    city = models.CharField(max_length=100, db_index=True)

    class Meta:
        # Prevent precise geographic parameter duplications
        unique_together = ('latitude', 'longitude')

class College(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True, db_index=True)
    slug = models.SlugField(max_length=255, unique=True)
    location = models.OneToOneField(GeoLocation, on_delete=models.PROTECT)

    def __str__(self):
        return self.name

```

---

## 5. Architectural Strategy for Scalability (C2C $\rightarrow$ B2C $\rightarrow$ B2B)

To avoid breaking schema changes down the line, this setup uses three core techniques:

1. **Account Type Separation (`User.AccountType`):** By separating users into `CONSUMER`, `VENDOR`, and `BUSINESS`, you can keep using the same base login logic while adding specialized tables later. For example, when you launch B2C, you can add a `VendorProfile` model linked to the user via a one-to-one relationship without touching the standard C2C profile table.
2. **Explicit Financial Ledgers:** The `Listing.price` field stores individual values directly. As you shift into high-volume B2B distribution tracking, you can introduce a new `BulkInventory` table that links directly to the base `Book` taxonomy, keeping your consumer database schemas clean.
3. **Location Decoupling:** Listings use optional `specific_college` and `specific_location` overrides. This design fits your current C2C college matching needs perfectly, but leaves the door open for commercial businesses to list massive stock levels across wider geographical regions or cities later on.

---

## 6. Clean Inter-App Data Flow Mapping

To keep coupling minimal, communication between applications flows through a distinct **Asset Pipeline Cycle**:

```
[Discovery Query Phase]
   Next.js/Mobile Clients call /api/v1/inventory/listings/
      ↳ Extracted via query: locations.College ID and locations.GeoLocation parameters.
      ↳ Performs an optimized Postgres SQL JOIN through `select_related('book', 'seller__profile__college')`.

[Intent & Match Action Phase]
   Buyer triggers "Contact Seller" link.
      ↳ System routes request payload to the communications tracking API.
      ↳ Formulates the WhatsApp redirect dynamic URL string (`wa.me/{phone}?text=Intent...`).
      ↳ Simultaneously records the matching metric row, leaving an open hook to transition to internal chat tables later.

```

Next, we can start writing the **Django REST Framework Serializers** for this model layer, or set up the **Geolocational query helpers** to compute real-time spatial indexing for your "Nearest Books" homepage feed. Which direction would you like to take?