from ckeditor_uploader.fields import RichTextUploadingField
from django.db import migrations, models
from django.utils.text import slugify


def populate_lesson_slugs(apps, schema_editor):
    Lesson = apps.get_model("core", "Lesson")
    for lesson in Lesson.objects.order_by("id"):
        base = slugify(lesson.title)[:180] or f"lesson-{lesson.pk}"
        candidate = base
        suffix = 2
        while (
            Lesson.objects.filter(slug=candidate)
            .exclude(pk=lesson.pk)
            .exists()
        ):
            candidate = f"{base}-{suffix}"
            suffix += 1
        Lesson.objects.filter(pk=lesson.pk).update(slug=candidate)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="lesson",
            name="slug",
            field=models.SlugField(
                blank=True,
                default="",
                help_text="Used in the lesson URL. Leave blank to generate it from the title.",
                max_length=200,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="lesson",
            name="body",
            field=RichTextUploadingField(
                blank=True,
                help_text="Full tutorial. Add headings, screenshots, tables and embedded media.",
            ),
        ),
        migrations.AddField(
            model_name="lesson",
            name="objectives",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="List of learning objectives shown at the top of the lesson.",
            ),
        ),
        migrations.AddField(
            model_name="lesson",
            name="key_takeaways",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="List of takeaways shown at the end of the lesson.",
            ),
        ),
        migrations.AddField(
            model_name="lesson",
            name="duration_minutes",
            field=models.PositiveIntegerField(default=10),
        ),
        migrations.AddField(
            model_name="lesson",
            name="is_published",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="lesson",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.RunPython(populate_lesson_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="lesson",
            name="slug",
            field=models.SlugField(
                blank=True,
                help_text="Used in the lesson URL. Leave blank to generate it from the title.",
                max_length=200,
                unique=True,
            ),
        ),
    ]
