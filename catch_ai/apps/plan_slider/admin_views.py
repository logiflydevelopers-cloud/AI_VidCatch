from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status

from .models import PlanSlide
from .serializers import PlanSlideSerializer
from apps.services.firebase_storage import upload_plan_slide, delete_file


# ==========================
# LIST + CREATE
# ==========================
@api_view(["GET", "POST"])
@permission_classes([IsAdminUser])
def plan_slides(request):

    # ==========================
    # GET → list
    # ==========================
    if request.method == "GET":
        slides = PlanSlide.objects.all().order_by("order", "-created_at")
        return Response(PlanSlideSerializer(slides, many=True).data)

    # ==========================
    # POST → create multiple
    # ==========================
    if request.method == "POST":

        files = request.FILES.getlist("media")

        if not files:
            return Response({"error": "At least one file required"}, status=400)

        base_order = int(request.data.get("order", 0))

        created_slides = []

        for index, file in enumerate(files):
            try:
                url, media_type = upload_plan_slide(file)
            except Exception as e:
                return Response({"error": str(e)}, status=400)

            slide = PlanSlide.objects.create(
                file_url=url,
                media_type=media_type,
                order=base_order + index   # ✅ auto increment
            )

            created_slides.append({
                "id": slide.id,
                "url": slide.file_url,
                "type": slide.media_type,
                "order": slide.order
            })

        return Response(created_slides, status=201)


# ==========================
# UPDATE + DELETE
# ==========================
@api_view(["PATCH", "DELETE"])
@permission_classes([IsAdminUser])
def plan_slide_detail(request, slide_id):

    try:
        slide = PlanSlide.objects.get(id=slide_id)
    except PlanSlide.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    # ==========================
    # PATCH → update
    # ==========================
    if request.method == "PATCH":

        file = request.FILES.get("media")

        # 🔥 If new media uploaded → replace
        if file:
            try:
                # delete old file
                delete_file(slide.file_url)

                url, media_type = upload_plan_slide(file)

                slide.file_url = url
                slide.media_type = media_type

            except Exception as e:
                return Response({"error": str(e)}, status=400)

        # update other fields
        order = request.data.get("order")
        is_active = request.data.get("is_active")

        if order is not None:
            slide.order = int(order)

        if is_active is not None:
            slide.is_active = is_active

        slide.save()

        return Response({
            "id": slide.id,
            "url": slide.file_url,
            "type": slide.media_type,
            "order": slide.order,
            "is_active": slide.is_active
        })

    # ==========================
    # DELETE
    # ==========================
    if request.method == "DELETE":

        # 🔥 delete file from Firebase
        delete_file(slide.file_url)

        slide.delete()

        return Response({"message": "Deleted"})
    