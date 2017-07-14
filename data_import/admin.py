from django.contrib import admin
from django.contrib.auth.models import Permission
from . import models
from .models import ContentPost, ContentPostImage,Information,TransRelation

from django.forms import TextInput, Textarea

from django import forms

from django.core.files.base import ContentFile
import os
from django.conf import settings
import platform
from .util import get_model_attrs
# Register your models here.

class TransRelationAdmin(admin.ModelAdmin):
    list_display = ('real_meaning', 'own_col', 'from_col')
    search_fields = ('real_meaning', 'own_col','from_col')
    list_filter = ('from_col',)

class ContentPostImageInline(admin.TabularInline):
    model = ContentPostImage
    extra = 3


class ContentPostAdminForm(forms.ModelForm):
    class Meta:
        model = ContentPost
        widgets = {
            'body': Textarea(attrs={'rows': 100, 'cols': 100}),
            'title': TextInput(attrs={'size': 40}),
        }
        exclude = ('html_file',)


class ContentPostAdmin(admin.ModelAdmin):

    form = ContentPostAdminForm
    inlines = [ContentPostImageInline, ]

    @staticmethod
    def delete_old_md_file():
        # delete old md files, this method is unused now
        md_file_list = []
        for contentpost in ContentPost.objects.all():
            if contentpost.md_file:
                md_file_list.append(contentpost.filename)

        with open('md_file_list.txt', 'wt') as f:
            f.write(str(md_file_list))

        for root, subdirs, files in os.walk(os.path.join(settings.MEDIA_ROOT, 'content/ContentPost')):
            for file in files:
                if file not in md_file_list:
                    os.remove(os.path.join(root, file))

    def save_model(self, request, obj, form, change):
        if obj:
            if obj.body:   # body有内容的时候才会更新md_file
                filename = obj.filename
                if filename != 'no md_file':
                    # On Windows file can't be removed so leave it
                    if platform.system() == "Windows":
                        pass
                    else:
                        obj.md_file.delete(save=False)   # 部署的时候存在,可以正常删除文件
                        obj.html_file.delete(save=False)
                # 没有md_file就根据title创建一个, 但不能创建html因为obj.save()的时候会创建
                obj.md_file.save(filename+'.md', ContentFile(obj.body), save=False)
                obj.md_file.close()
        obj.save()

class InformationAdmin(admin.ModelAdmin):
    list_display = ('id','title', 'subtitle', 'content', 'pub_date', 'last_edit_date', 'publisher', 'infotype')
    list_filter = ('infotype','publisher')

admin.site.register(Information,InformationAdmin)
admin.site.register(Permission)
admin.site.register(models.TransRelation,TransRelationAdmin)
admin.site.register(ContentPost, ContentPostAdmin)
