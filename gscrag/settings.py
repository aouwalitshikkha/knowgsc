"""
Django settings for gscrag project.
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = 'django-insecure-knowgsc-dev-key-change-me'

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ckeditor',
    'ckeditor_uploader',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'gscrag.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'gscrag.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'auth.User'

# ---------------------------------------------------------------------------
# CKEditor (lesson authoring)
# ---------------------------------------------------------------------------

CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_IMAGE_BACKEND = "pillow"
CKEDITOR_ALLOW_NONIMAGE_FILES = True
CKEDITOR_CONFIGS = {
    "default": {
        "toolbar": "KnowGSC",
        "toolbar_KnowGSC": [
            {"name": "document", "items": ["Source", "-", "Preview", "-", "Templates"]},
            {
                "name": "clipboard",
                "items": [
                    "Cut",
                    "Copy",
                    "Paste",
                    "PasteText",
                    "PasteFromWord",
                    "-",
                    "Undo",
                    "Redo",
                ],
            },
            {"name": "editing", "items": ["Find", "Replace", "-", "SelectAll"]},
            "/",
            {
                "name": "basicstyles",
                "items": [
                    "Bold",
                    "Italic",
                    "Underline",
                    "Strike",
                    "Subscript",
                    "Superscript",
                    "-",
                    "RemoveFormat",
                ],
            },
            {
                "name": "paragraph",
                "items": [
                    "NumberedList",
                    "BulletedList",
                    "-",
                    "Outdent",
                    "Indent",
                    "-",
                    "Blockquote",
                    "-",
                    "JustifyLeft",
                    "JustifyCenter",
                    "JustifyRight",
                    "JustifyBlock",
                ],
            },
            {"name": "links", "items": ["Link", "Unlink", "Anchor"]},
            {"name": "insert", "items": ["Image", "Table", "HorizontalRule", "SpecialChar", "Iframe"]},
            "/",
            {"name": "styles", "items": ["Styles", "Format", "Font", "FontSize"]},
            {"name": "colors", "items": ["TextColor", "BGColor"]},
            {"name": "tools", "items": ["Maximize", "ShowBlocks"]},
            {"name": "about", "items": ["About"]},
        ],
        "height": 560,
        "width": "100%",
        "allowedContent": True,
        "extraAllowedContent": "figure figcaption; img[!src,alt,width,height,loading]; iframe[*]",
        "removePlugins": "exportpdf",
        "image_previewText": " ",
    }
}

# ---------------------------------------------------------------------------
# RAG providers (all optional; KnowGSC works fully offline by default)
# ---------------------------------------------------------------------------

KNOWGSC_LLM_PROVIDER = os.environ.get("KNOWGSC_LLM_PROVIDER", "")
KNOWGSC_LLM_MODEL = os.environ.get("KNOWGSC_LLM_MODEL", "gpt-4o-mini")
KNOWGSC_LLM_BASE_URL = os.environ.get("KNOWGSC_LLM_BASE_URL", "")
KNOWGSC_LLM_API_KEY = os.environ.get("KNOWGSC_LLM_API_KEY", "")

KNOWGSC_EMBEDDING_PROVIDER = os.environ.get("KNOWGSC_EMBEDDING_PROVIDER", "")
KNOWGSC_EMBEDDING_MODEL = os.environ.get("KNOWGSC_EMBEDDING_MODEL", "text-embedding-3-small")
KNOWGSC_EMBEDDING_BASE_URL = os.environ.get("KNOWGSC_EMBEDDING_BASE_URL", "")
KNOWGSC_EMBEDDING_API_KEY = os.environ.get("KNOWGSC_EMBEDDING_API_KEY", "")
