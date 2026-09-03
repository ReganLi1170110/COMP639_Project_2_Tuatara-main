from urllib.parse import quote

from flask import render_template, request, redirect, url_for, flash, session, Response, abort
from werkzeug.utils import secure_filename

from app import flask_app as app
from app.repository import core_repository, knowhub_repository, user_repository
from app.repository import badge_repository
import app.utils as utils


CONTENT_ATTACHMENT_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "pdf", "doc", "docx", "ppt", "pptx", "txt","zip","csv"}
CONTENT_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}
MAX_NOTICE_ATTACHMENT_BYTES = 2 * 1024 * 1024


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _resolve_group_scope_for_user():
    """Resolve selected group scope for knowledge hub requests."""
    role = session.get("role")
    if role == "Admin":
        requested_group_id = _safe_int(request.values.get("group_id"))
        if requested_group_id is not None:
            return requested_group_id
        return session.get("knowledge_hub_group_id")
    return session.get("group_id")


def _knowledge_hub_redirect(group_id=None, active_tab=None):
    params = {}
    if group_id:
        params["group_id"] = group_id
    if active_tab:
        params["active_tab"] = active_tab
    if params:
        return redirect(url_for("knowledge_hub", **params))
    return redirect(url_for("knowledge_hub"))


def _coordinator_group_ids_for_user(user_id):
    return {
        group["group_id"]
        for group in core_repository.get_groups_by_user_id(user_id)
        if group.get("role") in {"Coordinator", "Group Coordinator"}
    }


def _filter_pending_knowledge_reviews_for_coordinator(user_id, pending_reviews):
    if not user_id:
        return []

    coordinator_group_ids = _coordinator_group_ids_for_user(user_id)
    if not coordinator_group_ids:
        return []

    author_group_cache = {}
    filtered_reviews = []
    for review in pending_reviews or []:
        author_id = review.get("author_id")
        if author_id not in author_group_cache:
            author_group_cache[author_id] = {
                group["group_id"]
                for group in core_repository.get_groups_by_user_id(author_id)
            }
        if coordinator_group_ids.intersection(author_group_cache[author_id]):
            filtered_reviews.append(review)

    return filtered_reviews


def _allowed_content_attachment(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in CONTENT_ATTACHMENT_EXTENSIONS


def _content_attachment_file_type(filename):
    extension = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    return "image" if extension in CONTENT_IMAGE_EXTENSIONS else "document"


def _save_content_attachments(uploaded_files):
    saved_files = []
    if not uploaded_files:
        return saved_files

    for file in uploaded_files:
        if not file or not file.filename:
            continue
        if not _allowed_content_attachment(file.filename):
            raise ValueError("Only images, PDFs, Word documents, PowerPoint files, and text files are allowed.")

        file_bytes = file.read()
        file_size = len(file_bytes or b"")

        if file_size > MAX_NOTICE_ATTACHMENT_BYTES:
            raise ValueError("Each attachment must be 2 MB or smaller.")

        original_name = secure_filename(file.filename)
        if not original_name:
            continue

        saved_files.append(
            {
                "filename": original_name,
                "file_type": _content_attachment_file_type(original_name),
                "mime_type": file.mimetype or "application/octet-stream",
                "file_bytes": file_bytes,
            }
        )

    return saved_files


def _draft_scope_post_redirect(group_id=None, edit_draft_id=None):
    params = {}
    if group_id:
        params["group_id"] = group_id
    if edit_draft_id:
        params["edit_draft_id"] = edit_draft_id
    if params:
        return redirect(url_for("knowledge_hub", **params))
    return redirect(url_for("knowledge_hub"))


def _group_notice_detail_redirect(update_id):
    return redirect(url_for("group_notice_detail", update_id=update_id))


def _knowledge_compose_redirect(compose_type, **params):
    if compose_type not in {"notice", "knowledge"}:
        return _knowledge_hub_redirect(_resolve_group_scope_for_user())
    return redirect(url_for("knowledge_hub_compose", compose_type=compose_type, **params))


@app.route("/knowledge-hub/attachment/<string:scope>/<int:attachment_id>", methods=["GET"])
@utils.login_required()
@utils.roles_required("Observer", "Operator", "Coordinator", "Admin")
def download_hub_attachment(scope, attachment_id):
    user_id = session.get("user_id")
    role = session.get("role")
    is_admin = role == "Admin"

    if scope == "update":
        attachment = knowhub_repository.get_update_attachment_by_id(attachment_id)
        if not attachment:
            abort(404)
        if not is_admin and not knowhub_repository.is_active_group_member(user_id, attachment["group_id"]):
            abort(403)
    elif scope == "knowledge":
        attachment = knowhub_repository.get_knowledge_attachment_by_id(attachment_id)
        if not attachment:
            abort(404)
        can_review_knowledge = role == "Coordinator"
        if not is_admin and not can_review_knowledge and attachment["status"] != knowhub_repository.PUBLISHED_STATUS and attachment["author_id"] != user_id:
            abort(403)
    else:
        abort(404)

    file_bytes = attachment.get("file_content") or b""
    mime_type = attachment.get("mime_type") or "application/octet-stream"
    filename = attachment.get("original_filename") or f"attachment_{attachment_id}"

    response = Response(file_bytes, mimetype=mime_type)
    response.headers["Content-Disposition"] = f"inline; filename*=UTF-8''{quote(filename)}"
    return response


@app.route("/knowledge-hub", methods=["GET"])
@utils.login_required()
@utils.roles_required("Observer", "Operator", "Coordinator", "Admin")
def knowledge_hub():
    user_id = session.get("user_id")
    role = session.get("role")
    is_admin = role == "Admin"

    selected_group_id = _resolve_group_scope_for_user()
    if is_admin:
        session["knowledge_hub_group_id"] = selected_group_id

    accessible_groups = []
    selected_group = None
    can_publish_group_notice = False

    if is_admin:
        accessible_groups = core_repository.get_all_groups_for_admin()
        if selected_group_id:
            selected_group = core_repository.get_group_by_id(selected_group_id)
            can_publish_group_notice = selected_group is not None and (is_admin or knowhub_repository.is_group_coordinator(user_id, selected_group_id))
    else:
        if selected_group_id:
            selected_group = core_repository.get_group_by_id(selected_group_id)
            can_publish_group_notice = is_admin or knowhub_repository.is_group_coordinator(user_id, selected_group_id)

    knowledge_categories = knowhub_repository.get_knowledge_categories()
    # Read optional search and category filters from query params
    q = (request.args.get('q') or '').strip() or None
    selected_category_id = _safe_int(request.args.get('category_id'))
    active_tab = (request.args.get('active_tab') or 'group-notices').strip().lower()
    if active_tab not in {'group-notices', 'knowledge-posts'}:
        active_tab = 'group-notices'
    knowledge_posts = knowhub_repository.get_knowledge_entries(user_id, limit=40, category_id=selected_category_id, q=q)
    editable_knowledge_statuses = [knowhub_repository.DRAFT_STATUS, knowhub_repository.PENDING_STATUS]
    if role == "Coordinator" or is_admin:
        editable_knowledge_statuses.append(knowhub_repository.PUBLISHED_STATUS)
    knowledge_drafts = knowhub_repository.get_user_knowledge_entries(
        user_id,
        statuses=editable_knowledge_statuses,
        limit=40,
    )
    can_review_content = role == "Coordinator"
    pending_knowledge_reviews = []
    if can_review_content:
        pending_knowledge_reviews = _filter_pending_knowledge_reviews_for_coordinator(
            user_id,
            knowhub_repository.get_pending_knowledge_entries(can_review_content, limit=40),
        )

    edit_draft_id = _safe_int(request.args.get("edit_draft_id"))
    editing_draft = None
    if edit_draft_id:
        draft = knowhub_repository.get_knowledge_entry_by_id(edit_draft_id)
        allowed_statuses = {knowhub_repository.DRAFT_STATUS, knowhub_repository.PENDING_STATUS}
        if role == "Coordinator" or is_admin:
            allowed_statuses.add(knowhub_repository.PUBLISHED_STATUS)

        # Determine edit permission: author or admin can edit; coordinators may edit
        # non-admin authors when they share a group.
        can_edit = False
        if draft and draft.get("status") in allowed_statuses:
            if draft.get("author_id") == user_id or is_admin:
                can_edit = True
            elif role == "Coordinator":
                try:
                    author = user_repository.get_user_by_id(draft.get("author_id")) if draft.get("author_id") else None
                    author_role = author.get("role") if author else None
                except Exception:
                    author_role = None
                if author_role != "Admin":
                    coordinator_group_ids = _coordinator_group_ids_for_user(user_id)
                    author_group_ids = {g["group_id"] for g in core_repository.get_groups_by_user_id(draft.get("author_id"))}
                    if coordinator_group_ids.intersection(author_group_ids):
                        can_edit = True

        if not draft or not can_edit:
            flash("Draft not found or cannot be edited.", "warning")
        else:
            editing_draft = draft
    
    edit_group_notice_id = _safe_int(request.args.get('edit_group_notice_id'))
    editing_notice = None
    if edit_group_notice_id:
        notice = knowhub_repository.get_group_notice_by_id(edit_group_notice_id)
        if not notice:
            flash('Group update not found or cannot be edited.', 'warning')
        else:
            if not (is_admin or knowhub_repository.is_group_coordinator(user_id, notice['group_id'])):
                flash('You are not allowed to edit this update.', 'danger')
            else:
                editing_notice = notice

    content_drafts = knowhub_repository.get_user_content_sharing(user_id, selected_group_id, limit=40)
    content_draft_attachments = knowhub_repository.get_update_attachments([item["update_id"] for item in content_drafts])

    pending_content_reviews = knowhub_repository.get_pending_content_reviews(selected_group_id, is_admin=is_admin, limit=40)
    pending_content_attachments = knowhub_repository.get_update_attachments([item["update_id"] for item in pending_content_reviews])

    can_create_content = True

    group_notices = knowhub_repository.get_group_notices(
        group_id=selected_group_id,
        current_user_id=user_id,
        is_admin=is_admin,
        limit=40,
    )
    group_notice_comments = knowhub_repository.get_group_notice_comments_for_updates(
        [notice["update_id"] for notice in group_notices],
        current_user_id=user_id,
    )
    # load edit histories for notices so templates can show edit timestamps
    notice_ids = [notice["update_id"] for notice in group_notices]
    edit_histories = knowhub_repository.get_edit_histories_for_updates(notice_ids)

    return render_template(
        "knowledge_hub.html",
        featured_posts=knowhub_repository.get_featured_knowledge_entries(limit=6),
        knowledge_posts=knowledge_posts,
        q=q,
        selected_category_id=selected_category_id,
        active_tab=active_tab,
        knowledge_categories=knowledge_categories,
        knowledge_drafts=knowledge_drafts,
        pending_knowledge_reviews=pending_knowledge_reviews,
        content_drafts=content_drafts,
        content_draft_attachments=content_draft_attachments,
        pending_content_reviews=pending_content_reviews,
        pending_content_attachments=pending_content_attachments,
        editing_draft=editing_draft,
        group_notices=group_notices,
        edit_histories=edit_histories,
        editing_notice=editing_notice,
        editing_notice_attachments=knowhub_repository.get_update_attachments([edit_group_notice_id]) if edit_group_notice_id else {},
        group_notice_comments=group_notice_comments,
        selected_group=selected_group,
        selected_group_id=selected_group_id,
        accessible_groups=accessible_groups,
        can_publish_group_notice=can_publish_group_notice,
        can_create_content=can_create_content,
        can_review_content=can_review_content,
        is_admin=is_admin,
        current_user_id=user_id,
        is_coordinator=(role == "Coordinator"),
    )



@app.route('/knowledge-hub/global/<int:entry_id>/feature', methods=['POST'])
@utils.login_required()
@utils.roles_required('Admin')
def toggle_feature_entry(entry_id):
    user_id = session.get('user_id')
    entry = knowhub_repository.get_knowledge_entry_by_id(entry_id)
    if not entry or entry.get('status') != knowhub_repository.PUBLISHED_STATUS:
        flash('Knowledge post not found or must be published to feature.', 'warning')
        return _knowledge_hub_redirect(active_tab="knowledge-posts")

    # Expecting a form field 'set' with '1' to feature or '0' to unfeature
    set_val = request.form.get('set')
    target = True if set_val in ('1', 'true', 'True') else False
    updated = knowhub_repository.set_knowledge_entry_featured(entry_id, target)
    if updated:
        flash('Knowledge post featured.' if target else 'Knowledge post unfeatured.', 'success')
    else:
        flash('Failed to update featured status.', 'danger')
    return _knowledge_hub_redirect(active_tab="knowledge-posts")


@app.route("/knowledge-hub/compose/<string:compose_type>", methods=["GET"])
@utils.login_required()
@utils.roles_required("Observer", "Operator", "Coordinator", "Admin")
def knowledge_hub_compose(compose_type):
    user_id = session["user_id"]
    role = session.get("role")
    is_admin = role == "Admin"
    compose_type = (compose_type or "").strip().lower()

    if compose_type not in {"notice", "knowledge"}:
        flash("Invalid compose page.", "warning")
        return _knowledge_hub_redirect(_resolve_group_scope_for_user())

    knowledge_categories = knowhub_repository.get_knowledge_categories()
    editable_knowledge_statuses = [knowhub_repository.DRAFT_STATUS, knowhub_repository.PENDING_STATUS]
    if role == "Coordinator" or is_admin:
        editable_knowledge_statuses.append(knowhub_repository.PUBLISHED_STATUS)
    knowledge_drafts = knowhub_repository.get_user_knowledge_entries(
        user_id,
        statuses=editable_knowledge_statuses,
        limit=20,
    )
    can_review_content = role == "Coordinator"
    pending_knowledge_reviews = []
    if can_review_content:
        pending_knowledge_reviews = _filter_pending_knowledge_reviews_for_coordinator(
            user_id,
            knowhub_repository.get_pending_knowledge_entries(can_review_content, limit=20),
        )
    selected_group_id = None
    selected_group = None
    accessible_groups = []
    can_publish_group_notice = False
    group_notice_drafts = []
    editing_draft = None
    editing_notice = None
    edit_group_notice_id = None

    if compose_type == "notice":
        selected_group_id = _safe_int(request.args.get("group_id"))
        if is_admin:
            accessible_groups = core_repository.get_all_groups_for_admin()
            if selected_group_id is None:
                selected_group_id = session.get("knowledge_hub_group_id")
        else:
            if selected_group_id is None:
                selected_group_id = session.get("group_id")

        if selected_group_id:
            selected_group = core_repository.get_group_by_id(selected_group_id)
            can_publish_group_notice = is_admin or knowhub_repository.is_active_group_member(user_id, selected_group_id)
            group_notice_drafts = knowhub_repository.get_user_group_notice_drafts(user_id, selected_group_id, limit=20)

        edit_group_notice_id = _safe_int(request.args.get("edit_group_notice_id"))
        if edit_group_notice_id:
            notice = knowhub_repository.get_group_notice_by_id(edit_group_notice_id)
            if not notice:
                flash("Group update not found or cannot be edited.", "warning")
                return _knowledge_hub_redirect(selected_group_id)

            if notice["author_id"] != user_id and not (is_admin or knowhub_repository.is_group_coordinator(user_id, notice["group_id"])):
                flash("You are not allowed to edit this notice.", "danger")
                return _knowledge_hub_redirect(notice["group_id"])

            editing_notice = notice
            selected_group_id = notice["group_id"]
            selected_group = core_repository.get_group_by_id(selected_group_id)
            can_publish_group_notice = is_admin or knowhub_repository.is_active_group_member(user_id, selected_group_id)
            group_notice_drafts = knowhub_repository.get_user_group_notice_drafts(user_id, selected_group_id, limit=20)
    else:
        edit_draft_id = _safe_int(request.args.get("edit_draft_id"))
        if edit_draft_id:
            draft = knowhub_repository.get_knowledge_entry_by_id(edit_draft_id)
            allowed_statuses = {knowhub_repository.DRAFT_STATUS, knowhub_repository.PENDING_STATUS}
            if role == "Coordinator" or is_admin:
                allowed_statuses.add(knowhub_repository.PUBLISHED_STATUS)

            can_edit = False
            if draft and draft.get("status") in allowed_statuses:
                if draft.get("author_id") == user_id or is_admin:
                    can_edit = True
                elif role == "Coordinator":
                    try:
                        author = user_repository.get_user_by_id(draft.get("author_id")) if draft.get("author_id") else None
                        author_role = author.get("role") if author else None
                    except Exception:
                        author_role = None
                    if author_role != "Admin":
                        coordinator_group_ids = _coordinator_group_ids_for_user(user_id)
                        author_group_ids = {g["group_id"] for g in core_repository.get_groups_by_user_id(draft.get("author_id"))}
                        if coordinator_group_ids.intersection(author_group_ids):
                            can_edit = True

            if not draft or not can_edit:
                flash("Draft not found or cannot be edited.", "warning")
                return _knowledge_hub_redirect(active_tab="knowledge-posts")
            editing_draft = draft
            editing_draft_attachments = knowhub_repository.get_knowledge_attachments([edit_draft_id]).get(edit_draft_id, [])

    return render_template(
        "knowledge_compose.html",
        compose_type=compose_type,
        knowledge_categories=knowledge_categories,
        knowledge_drafts=knowledge_drafts,
        selected_group=selected_group,
        selected_group_id=selected_group_id,
        accessible_groups=accessible_groups,
        can_publish_group_notice=can_publish_group_notice,
        group_notice_drafts=group_notice_drafts,
        editing_draft=editing_draft,
        editing_draft_attachments=editing_draft_attachments if 'editing_draft_attachments' in locals() else [],
        editing_notice=editing_notice,
        editing_notice_attachments=knowhub_repository.get_update_attachments([edit_group_notice_id]) if edit_group_notice_id else [],
        can_review_content=can_review_content,
        pending_knowledge_reviews=pending_knowledge_reviews,
        is_admin=is_admin,
        role=role,
        current_user_id=user_id,
        is_coordinator=(role == "Coordinator"),
        return_to=(request.args.get('return_to') or None),
    )


@app.route("/knowledge-hub/group/<int:update_id>", methods=["GET"])
@utils.login_required()
@utils.roles_required("Observer", "Operator", "Coordinator", "Admin")
def group_notice_detail(update_id):
    user_id = session["user_id"]
    role = session.get("role")
    is_admin = role == "Admin"

    notice = knowhub_repository.get_group_notice_detail(update_id, current_user_id=user_id)
    if not notice:
        flash("Group update not found.", "warning")
        return _knowledge_hub_redirect(_resolve_group_scope_for_user())

    if not is_admin and not knowhub_repository.is_active_group_member(user_id, notice["group_id"]):
        flash("You can only view notices in your group.", "danger")
        return _knowledge_hub_redirect(_resolve_group_scope_for_user())

    comments = knowhub_repository.get_group_notice_comments_for_updates([update_id], current_user_id=user_id).get(update_id, [])
    attachments = knowhub_repository.get_update_attachments([update_id]).get(update_id, [])
    edit_history = knowhub_repository.get_group_notice_edit_history(update_id)
    current_version_number = len(edit_history) + 1
    can_edit_notice = is_admin or knowhub_repository.is_group_coordinator(user_id, notice["group_id"])
    can_delete_notice = is_admin or notice["author_id"] == user_id or knowhub_repository.is_group_coordinator(user_id, notice["group_id"])
    can_moderate_comments = is_admin or knowhub_repository.is_group_coordinator(user_id, notice["group_id"])

    return render_template(
        "group_notice_detail.html",
        detail_type="notice",
        notice=notice,
        comments=comments,
        attachments=attachments,
        edit_history=edit_history,
        current_version_number=current_version_number,
        can_edit_notice=can_edit_notice,
        can_delete_notice=can_delete_notice,
        can_moderate_comments=can_moderate_comments,
        selected_group_id=notice["group_id"],
        selected_group=core_repository.get_group_by_id(notice["group_id"]),
        is_admin=is_admin,
        current_user_id=user_id,
        is_coordinator=(role == "Coordinator"),
    )


@app.route("/knowledge-hub/global/publish", methods=["POST"])
@utils.login_required()
@utils.roles_required("Observer", "Operator", "Coordinator", "Admin")
def publish_global_post():
    user_id = session["user_id"]
    role = session.get("role")
    is_admin = role == "Admin"
    title = (request.form.get("title") or "").strip()
    content = (request.form.get("content") or "").strip()
    content_action = (request.form.get("content_action") or "save_draft").strip().lower()
    draft_id = _safe_int(request.form.get("draft_id"))
    category_id = _safe_int(request.form.get("category_id"))
    image_url = (request.form.get("image_url") or "").strip() or None

    if not title or not content:
        flash("Knowledge title and content are required.", "danger")
        return _knowledge_hub_redirect()

    if not category_id:
        flash("Knowledge category is required.", "danger")
        if request.form.get("return_to") == 'compose':
            return _knowledge_compose_redirect('knowledge', edit_draft_id=draft_id) if draft_id else _knowledge_compose_redirect('knowledge')
        return _knowledge_hub_redirect(active_tab="knowledge-posts")

    if content_action not in {"save_draft", "submit_for_approval", "save_published"}:
        content_action = "save_draft"

    uploaded_files = request.files.getlist("attachments")
    remove_files = request.form.getlist("remove_attachment")
    return_to = (request.form.get("return_to") or "").strip()

    if draft_id:
        draft = knowhub_repository.get_knowledge_entry_by_id(draft_id)
        if not draft:
            flash("Draft not found.", "warning")
            return _knowledge_hub_redirect(active_tab="knowledge-posts")

        # Determine whether the current user may update this draft.
        can_update = False
        if draft.get("author_id") == user_id or is_admin:
            can_update = True
        elif role == "Coordinator":
            # Coordinators may edit published posts, or drafts by non-admin authors in groups they coordinate.
            if draft.get("status") == knowhub_repository.PUBLISHED_STATUS:
                can_update = True
            else:
                try:
                    author = user_repository.get_user_by_id(draft.get("author_id")) if draft.get("author_id") else None
                    author_role = author.get("role") if author else None
                except Exception:
                    author_role = None
                if author_role != "Admin":
                    coordinator_group_ids = _coordinator_group_ids_for_user(user_id)
                    author_group_ids = {g["group_id"] for g in core_repository.get_groups_by_user_id(draft.get("author_id"))}
                    if coordinator_group_ids.intersection(author_group_ids):
                        can_update = True

        if not can_update:
            flash("Draft not found.", "warning")
            return _knowledge_hub_redirect(active_tab="knowledge-posts")

        if draft["status"] == knowhub_repository.PUBLISHED_STATUS:
            if not (is_admin or role == "Coordinator"):
                flash("Only Coordinators can edit approved knowledge posts.", "danger")
                return _knowledge_hub_redirect()
            # Published edits remain published.
            status = knowhub_repository.PUBLISHED_STATUS
        elif draft["status"] in {knowhub_repository.DRAFT_STATUS, knowhub_repository.PENDING_STATUS}:
            status = knowhub_repository.DRAFT_STATUS if content_action == "save_draft" else knowhub_repository.PENDING_STATUS
        else:
            flash("This knowledge post cannot be edited.", "warning")
            return _knowledge_hub_redirect(active_tab="knowledge-posts")

        updated_id = knowhub_repository.update_knowledge_entry(draft_id, user_id, title, content, category_id=category_id, image_url=image_url, status=status)
        update_id = updated_id or draft_id
        # handle attachments: remove requested and save newly uploaded
        try:
            if remove_files:
                for attachment_id_text in remove_files:
                    attachment_id = _safe_int(attachment_id_text)
                    if attachment_id:
                        knowhub_repository.delete_knowledge_attachment(attachment_id, update_id, user_id)
            saved_files = _save_content_attachments(uploaded_files)
            for attachment in saved_files:
                knowhub_repository.add_knowledge_attachment(
                    update_id,
                    attachment["file_type"],
                    attachment["filename"],
                    attachment["file_bytes"],
                    mime_type=attachment["mime_type"],
                    description=attachment["filename"],
                )
                if attachment["file_type"] == "image":
                    try:
                        badge_repository.add_user_points(user_id, badge_repository.BadgeAction.PHOTO_UPLOAD, 'Uploaded photo')
                    except Exception:
                        pass
        except ValueError as exc:
            flash(str(exc), "danger")
            if return_to == 'compose':
                return _knowledge_compose_redirect('knowledge', edit_draft_id=update_id)
            return _knowledge_hub_redirect(active_tab="knowledge-posts")
    else:
        status = knowhub_repository.DRAFT_STATUS if content_action == "save_draft" else knowhub_repository.PENDING_STATUS
        update_id = knowhub_repository.create_knowledge_entry(
            user_id,
            title,
            content,
            category_id=category_id,
            image_url=image_url,
            status=status,
        )

    # if new post was created (no draft_id provided), save any uploaded files
    if not draft_id and update_id:
        try:
            saved_files = _save_content_attachments(uploaded_files)
            for attachment in saved_files:
                knowhub_repository.add_knowledge_attachment(
                    update_id,
                    attachment["file_type"],
                    attachment["filename"],
                    attachment["file_bytes"],
                    mime_type=attachment["mime_type"],
                    description=attachment["filename"],
                )
                if attachment["file_type"] == "image":
                    try:
                        badge_repository.add_user_points(user_id, badge_repository.BadgeAction.PHOTO_UPLOAD, 'Uploaded photo')
                    except Exception:
                        pass
        except ValueError as exc:
            flash(str(exc), "danger")
            if return_to == 'compose':
                return _knowledge_compose_redirect('knowledge')
            return _knowledge_hub_redirect(active_tab="knowledge-posts")

    if status == knowhub_repository.PUBLISHED_STATUS:
        flash("Knowledge post changes saved.", "success")
        try:
            if update_id:
                badge_repository.add_user_points(user_id, badge_repository.BadgeAction.KNOWLEDGE_POST, 'Published knowledge post')
        except Exception:
            pass
    elif status == knowhub_repository.DRAFT_STATUS:
        flash("Knowledge post saved as draft.", "success")
    else:
        flash("Knowledge post submitted for approval.", "success")
    if return_to == 'compose':
        if status == knowhub_repository.DRAFT_STATUS and update_id:
            return _knowledge_compose_redirect('knowledge', edit_draft_id=update_id)
        return _knowledge_compose_redirect('knowledge')
    if return_to == 'detail' and update_id:
        return redirect(url_for('knowledge_post_detail', entry_id=update_id))
    return _knowledge_hub_redirect(active_tab="knowledge-posts")



@app.route("/knowledge-hub/global/draft/<int:update_id>/edit", methods=["GET"])
@utils.login_required()
@utils.roles_required("Observer", "Operator", "Coordinator", "Admin")
def edit_global_draft(update_id):
    user_id = session["user_id"]
    role = session.get("role")
    is_admin = role == "Admin"

    draft = knowhub_repository.get_knowledge_entry_by_id(update_id)
    if not draft:
        flash("Draft not found or cannot be edited.", "warning")
        return _knowledge_hub_redirect()

    allowed_statuses = {knowhub_repository.DRAFT_STATUS, knowhub_repository.PENDING_STATUS}
    if role == "Coordinator" or is_admin:
        allowed_statuses.add(knowhub_repository.PUBLISHED_STATUS)

    can_edit = False
    if draft.get("status") in allowed_statuses:
        if draft.get("author_id") == user_id or is_admin:
            can_edit = True
        elif role == "Coordinator":
            try:
                author = user_repository.get_user_by_id(draft.get("author_id")) if draft.get("author_id") else None
                author_role = author.get("role") if author else None
            except Exception:
                author_role = None
            if author_role != "Admin":
                coordinator_group_ids = _coordinator_group_ids_for_user(user_id)
                author_group_ids = {g["group_id"] for g in core_repository.get_groups_by_user_id(draft.get("author_id"))}
                if coordinator_group_ids.intersection(author_group_ids):
                    can_edit = True

    if not can_edit:
        flash("Draft not found or cannot be edited.", "warning")
        return _knowledge_hub_redirect()

    # When editing from the post detail page, keep a return_to flag so the form can redirect back.
    return _knowledge_compose_redirect("knowledge", edit_draft_id=update_id, return_to='detail')


@app.route("/knowledge-hub/global/draft/<int:update_id>/delete", methods=["POST"])
@utils.login_required()
@utils.roles_required("Observer", "Operator", "Coordinator", "Admin")
def delete_global_draft(update_id):
    user_id = session["user_id"]
    draft = knowhub_repository.get_knowledge_entry_by_id(update_id)
    if not draft:
        flash("Draft not found.", "warning")
        return _knowledge_hub_redirect()

    if draft["status"] not in {knowhub_repository.DRAFT_STATUS, knowhub_repository.PENDING_STATUS}:
        flash("Only drafts can be deleted from this action.", "warning")
        return _knowledge_hub_redirect()

    if draft["author_id"] != user_id and session.get("role") != "Admin":
        flash("You are not allowed to delete this draft.", "danger")
        return _knowledge_hub_redirect(active_tab="knowledge-posts")

    knowhub_repository.delete_knowledge_entry(update_id)
    flash("Draft deleted.", "success")
    return _knowledge_hub_redirect(active_tab="knowledge-posts")


@app.route("/knowledge-hub/global/<int:update_id>/approve", methods=["POST"])
@utils.login_required()
@utils.roles_required("Coordinator", "Admin")
def approve_content_sharing(update_id):
    user_id = session["user_id"]
    role = session.get("role")
    content_item = knowhub_repository.get_knowledge_entry_by_id(update_id)
    if not content_item or content_item["status"] != knowhub_repository.PENDING_STATUS:
        flash("Content not found for approval.", "warning")
        return _knowledge_hub_redirect()

    author_id = content_item.get("author_id")
    author = user_repository.get_user_by_id(author_id) if author_id else None
    author_role = author.get("role") if author else None

    # If the author is an Admin, only an Admin approving their own post is allowed.
    if author_role == "Admin":
        if role != "Admin" or user_id != author_id:
            flash("You are not allowed to approve this content.", "danger")
            return _knowledge_hub_redirect()

    else:
        # Non-admin authors: coordinators may approve if they share a group with the author.
        if role == "Coordinator":
            coordinator_group_ids = _coordinator_group_ids_for_user(user_id)
            author_group_ids = {
                group["group_id"]
                for group in core_repository.get_groups_by_user_id(author_id)
            }
            if not coordinator_group_ids.intersection(author_group_ids):
                flash("You are not allowed to approve this content.", "danger")
                return _knowledge_hub_redirect()

    knowhub_repository.approve_knowledge_entry(update_id, user_id)
    flash("Knowledge post approved and published.", "success")
    return_to = (request.form.get("return_to") or "").strip()
    if return_to == 'compose':
        return _knowledge_compose_redirect('knowledge')
    return _knowledge_hub_redirect()

@app.route('/knowledge-hub/global/<int:entry_id>', methods=['GET'])
@utils.login_required()
@utils.roles_required('Observer', 'Operator', 'Coordinator', 'Admin')
def knowledge_post_detail(entry_id):
    user_id = session.get('user_id')
    post = knowhub_repository.get_knowledge_entry_by_id(entry_id)
    if not post or post.get('status') != knowhub_repository.PUBLISHED_STATUS:
        flash('Knowledge post not found or not published.', 'warning')
        return _knowledge_hub_redirect()

    edit_history = knowhub_repository.get_knowledge_entry_edit_history(entry_id)
    current_version_number = post.get('version_number') or (len(edit_history) + 1)

    # Reuse the shared detail template with a notice-like payload.
    detail_payload = {
        'update_id': post.get('entry_id'),
        'group_id': None,
        'group_name': 'Platform-wide',
        'author_id': post.get('author_id'),
        'title': post.get('title'),
        'content': post.get('content'),
        'created_at': post.get('created_at'),
        'updated_at': post.get('updated_at'),
        'status': post.get('status'),
        'author_name': post.get('author_name'),
        'category_name': post.get('category_name'),
        'image_url': post.get('image_url'),
        'likes_count': 0,
        'comments_count': 0,
        'user_liked': False,
    }

    attachments = knowhub_repository.get_knowledge_attachments([entry_id]).get(entry_id, [])
    if post.get('image_url'):
        attachments.append({'file_type': 'image', 'file_url': post.get('image_url'), 'description': 'image'})
    # Compute precise edit rights: Admins can edit any; Coordinators can edit non-Admin authors
    # when they share at least one group. Others cannot.
    can_edit_knowledge = False
    role = session.get('role')
    if role == 'Admin':
        can_edit_knowledge = True
    elif role == 'Coordinator':
        author_id = post.get('author_id')
        try:
            author = user_repository.get_user_by_id(author_id) if author_id else None
            author_role = author.get('role') if author else None
        except Exception:
            author_role = None
        if author_role != 'Admin':
            coordinator_group_ids = _coordinator_group_ids_for_user(user_id)
            author_group_ids = {g['group_id'] for g in core_repository.get_groups_by_user_id(author_id)}
            if coordinator_group_ids.intersection(author_group_ids):
                can_edit_knowledge = True

    return render_template(
        'group_notice_detail.html',
        detail_type='knowledge',
        notice=detail_payload,
        comments=[],
        attachments=attachments,
        edit_history=edit_history,
        current_version_number=current_version_number,
        can_delete_notice=False,
        can_moderate_comments=False,
        can_edit_knowledge=can_edit_knowledge,
        selected_group_id=None,
        selected_group=None,
        is_admin=(session.get('role') == 'Admin'),
        current_user_id=user_id,
        is_coordinator=(session.get('role') == 'Coordinator'),
    )


@app.route("/knowledge-hub/global/<int:update_id>/return", methods=["POST"])
@utils.login_required()
@utils.roles_required("Coordinator", "Admin")
def return_content_to_draft(update_id):
    user_id = session["user_id"]
    role = session.get("role")
    is_admin = role == "Admin"
    content_item = knowhub_repository.get_knowledge_entry_by_id(update_id)
    if not content_item or content_item["status"] != knowhub_repository.PENDING_STATUS:
        flash("Content not found for review.", "warning")
        return _knowledge_hub_redirect()

    if not is_admin and role != "Coordinator":
        flash("You are not allowed to review this content.", "danger")
        return _knowledge_hub_redirect()

    knowhub_repository.return_knowledge_entry_to_draft(update_id)
    flash("Knowledge post returned to draft.", "success")
    return_to = (request.form.get("return_to") or "").strip()
    if return_to == 'compose':
        return _knowledge_compose_redirect('knowledge')
    return _knowledge_hub_redirect()


@app.route("/knowledge-hub/global/<int:entry_id>/comment", methods=["POST"])
@utils.login_required()
@utils.roles_required("Observer", "Operator", "Coordinator", "Admin")
def comment_global_post(entry_id):
    flash("Knowledge posts do not support comments.", "warning")
    return _knowledge_hub_redirect(_resolve_group_scope_for_user())


@app.route("/knowledge-hub/global/<int:entry_id>/like", methods=["POST"])
@utils.login_required()
@utils.roles_required("Observer", "Operator", "Coordinator", "Admin")
def toggle_like_global_post(entry_id):
    flash("Knowledge posts do not support likes.", "warning")
    return _knowledge_hub_redirect(_resolve_group_scope_for_user())


@app.route("/knowledge-hub/global/<int:entry_id>/delete", methods=["POST"])
@utils.login_required()
@utils.roles_required("Observer", "Operator", "Coordinator", "Admin")
def delete_global_post(entry_id):
    user_id = session["user_id"]
    role = session.get("role")
    is_admin = role == "Admin"

    post = knowhub_repository.get_knowledge_entry_by_id(entry_id)
    if not post:
        flash("Knowledge post not found.", "warning")
        return _knowledge_hub_redirect(active_tab="knowledge-posts")

    if not is_admin and post["author_id"] != user_id:
        flash("You are not allowed to delete this post.", "danger")
        return _knowledge_hub_redirect(active_tab="knowledge-posts")

    knowhub_repository.delete_knowledge_entry(entry_id)
    flash("Knowledge post deleted.", "success")
    return _knowledge_hub_redirect(active_tab="knowledge-posts")


@app.route("/knowledge-hub/global/comment/<int:comment_id>/delete", methods=["POST"])
@utils.login_required()
@utils.roles_required("Observer", "Operator", "Coordinator", "Admin")
def delete_global_comment(comment_id):
    flash("Knowledge posts do not support comments.", "warning")
    return _knowledge_hub_redirect(_resolve_group_scope_for_user())


@app.route("/knowledge-hub/group/publish", methods=["POST"])
@utils.login_required()
@utils.roles_required("Observer", "Operator", "Coordinator", "Admin")
def publish_group_notice():
    user_id = session["user_id"]
    role = session.get("role")
    is_admin = role == "Admin"

    group_id = _resolve_group_scope_for_user()
    title = (request.form.get("title") or "").strip()
    content = (request.form.get("content") or "").strip()
    content_action = (request.form.get("content_action") or "publish").strip().lower()
    uploaded_files = request.files.getlist("attachments")

    if not group_id:
        flash("Please select a group before publishing a group update.", "danger")
        return _knowledge_hub_redirect()

    if not title or not content:
        flash("Group update title and content are required.", "danger")
        return _knowledge_hub_redirect(group_id)

    if content_action not in {"draft", "publish"}:
        content_action = "publish"

    if not (is_admin or knowhub_repository.is_group_coordinator(user_id, group_id)):
        flash("Only an admin or group coordinator can draft or publish group updates.", "danger")
        return _knowledge_hub_redirect(group_id)

    status = knowhub_repository.DRAFT_STATUS if content_action == "draft" else knowhub_repository.PUBLISHED_STATUS

    # support editing existing notice when 'notice_id' present
    notice_id = _safe_int(request.form.get('notice_id'))
    if notice_id:
        notice = knowhub_repository.get_group_notice_by_id(notice_id)
        if not notice:
            flash("Update not found.", "warning")
            return _knowledge_hub_redirect(group_id)

        if not (is_admin or knowhub_repository.is_group_coordinator(user_id, group_id)):
            flash("Only an admin or group coordinator can edit group updates.", "danger")
            return _knowledge_hub_redirect(group_id)

        updated = knowhub_repository.update_group_notice(notice_id, user_id, group_id, title, content, status=status)
        if updated:
            try:
                saved_files = _save_content_attachments(uploaded_files)
                for attachment in saved_files:
                    knowhub_repository.add_update_attachment(
                        notice_id,
                        attachment["file_type"],
                        attachment["filename"],
                        attachment["file_bytes"],
                        mime_type=attachment["mime_type"],
                        description=attachment["filename"],
                    )
                    if attachment["file_type"] == "image":
                        try:
                            badge_repository.add_user_points(user_id, badge_repository.BadgeAction.PHOTO_UPLOAD, 'Uploaded photo')
                        except Exception:
                            pass
            except ValueError as exc:
                flash(str(exc), "danger")
                return _knowledge_compose_redirect("notice", group_id=group_id, edit_group_notice_id=notice_id)

            flash("Group update updated as draft." if status == knowhub_repository.DRAFT_STATUS else "Group update updated and published.", "success")
            if status == knowhub_repository.DRAFT_STATUS:
                return _knowledge_compose_redirect("notice", group_id=group_id, edit_group_notice_id=notice_id)
        else:
            flash("Failed to update notice.", "danger")
        return _knowledge_hub_redirect(group_id)

    update_id = knowhub_repository.create_group_notice(group_id, user_id, title, content, status=status)
    if update_id:
        try:
            saved_files = _save_content_attachments(uploaded_files)
            for attachment in saved_files:
                knowhub_repository.add_update_attachment(
                    update_id,
                    attachment["file_type"],
                    attachment["filename"],
                    attachment["file_bytes"],
                    mime_type=attachment["mime_type"],
                    description=attachment["filename"],
                )
                if attachment["file_type"] == "image":
                    try:
                        badge_repository.add_user_points(user_id, badge_repository.BadgeAction.PHOTO_UPLOAD, 'Uploaded photo')
                    except Exception:
                        pass
        except ValueError as exc:
            flash(str(exc), "danger")
            return _knowledge_compose_redirect("notice", group_id=group_id, edit_group_notice_id=update_id)

    flash("Group update saved as draft." if status == knowhub_repository.DRAFT_STATUS else "Group update published.", "success")
    try:
        if status == knowhub_repository.PUBLISHED_STATUS and update_id:
            badge_repository.add_user_points(user_id, badge_repository.BadgeAction.KNOWLEDGE_POST, 'Published group notice')
    except Exception:
        pass
    if status == knowhub_repository.DRAFT_STATUS and update_id:
        return _knowledge_compose_redirect("notice", group_id=group_id, edit_group_notice_id=update_id)
    return _knowledge_hub_redirect(group_id)



@app.route('/knowledge-hub/group/<int:update_id>/edit', methods=['GET'])
@utils.login_required()
@utils.roles_required('Observer', 'Operator', 'Coordinator', 'Admin')
def edit_group_notice(update_id):
    user_id = session['user_id']
    role = session.get('role')
    is_admin = role == 'Admin'
    notice = knowhub_repository.get_group_notice_by_id(update_id)
    if not notice:
        flash('Update not found.', 'warning')
        return _knowledge_hub_redirect(_resolve_group_scope_for_user())

    if not (is_admin or knowhub_repository.is_group_coordinator(user_id, notice['group_id'])):
        flash('Only an admin or group coordinator can edit this update.', 'danger')
        return _knowledge_hub_redirect(_resolve_group_scope_for_user())

    return _knowledge_compose_redirect('notice', group_id=notice['group_id'], edit_group_notice_id=update_id)


@app.route("/knowledge-hub/group/<int:update_id>/comment", methods=["POST"])
@utils.login_required()
@utils.roles_required("Observer", "Operator", "Coordinator", "Admin")
def comment_group_notice(update_id):
    user_id = session["user_id"]
    role = session.get("role")
    is_admin = role == "Admin"

    notice = knowhub_repository.get_group_notice_by_id(update_id)
    if not notice or notice["status"] != knowhub_repository.PUBLISHED_STATUS:
        flash("Group update not found.", "warning")
        return _knowledge_hub_redirect(_resolve_group_scope_for_user())

    if not is_admin and not knowhub_repository.is_active_group_member(user_id, notice["group_id"]):
        flash("You can only comment on notices for your group.", "danger")
        return _knowledge_hub_redirect(_resolve_group_scope_for_user())

    comment_text = (request.form.get("comment_text") or "").strip()
    if not comment_text:
        flash("Comment cannot be empty.", "danger")
        return _knowledge_hub_redirect(_resolve_group_scope_for_user())

    knowhub_repository.add_group_notice_comment(update_id, user_id, comment_text)
    flash("Comment added.", "success")
    next_url = request.form.get("next")
    if next_url:
        return redirect(next_url)
    return _knowledge_hub_redirect(_resolve_group_scope_for_user())


@app.route("/knowledge-hub/group/<int:update_id>/like", methods=["POST"])
@utils.login_required()
@utils.roles_required("Observer", "Operator", "Coordinator", "Admin")
def toggle_like_group_notice(update_id):
    user_id = session["user_id"]
    role = session.get("role")
    is_admin = role == "Admin"

    notice = knowhub_repository.get_group_notice_by_id(update_id)
    if not notice or notice["status"] != knowhub_repository.PUBLISHED_STATUS:
        flash("Group update not found.", "warning")
        return _knowledge_hub_redirect(_resolve_group_scope_for_user())

    if not is_admin and not knowhub_repository.is_active_group_member(user_id, notice["group_id"]):
        flash("You can only interact with notices in your group.", "danger")
        return _knowledge_hub_redirect(_resolve_group_scope_for_user())

    liked = knowhub_repository.toggle_group_notice_like(update_id, user_id)
    flash("Notice liked." if liked else "Like removed.", "success")
    if liked:
        try:
            badge_repository.add_user_points(user_id, badge_repository.BadgeAction.LIKE, 'Liked group notice')
        except Exception:
            pass
    next_url = request.form.get("next")
    if next_url:
        return redirect(next_url)
    return _knowledge_hub_redirect(_resolve_group_scope_for_user())


@app.route("/knowledge-hub/group/<int:update_id>/delete", methods=["POST"])
@utils.login_required()
@utils.roles_required("Observer", "Operator", "Coordinator", "Admin")
def delete_group_notice(update_id):
    user_id = session["user_id"]
    role = session.get("role")
    is_admin = role == "Admin"

    notice = knowhub_repository.get_group_notice_by_id(update_id)
    if not notice:
        flash("Group update not found.", "warning")
        return _knowledge_hub_redirect(_resolve_group_scope_for_user())

    if not (is_admin or notice["author_id"] == user_id or knowhub_repository.is_group_coordinator(user_id, notice["group_id"])):
        flash("You are not allowed to delete this update.", "danger")
        return _knowledge_hub_redirect(_resolve_group_scope_for_user())

    deletion_reason = (request.form.get("deletion_reason") or "").strip()
    if not deletion_reason:
        flash("Please provide a reason before deleting the notice.", "warning")
        return _knowledge_hub_redirect(_resolve_group_scope_for_user())

    knowhub_repository.log_deleted_comment(
        original_comment_id=None,
        update_id=notice["update_id"],
        author_id=notice["author_id"],
        moderator_id=user_id,
        content_snapshot=notice["content"],
        deletion_reason=deletion_reason,
    )
    knowhub_repository.delete_group_notice(update_id)
    flash("Group update deleted.", "success")
    return _knowledge_hub_redirect(_resolve_group_scope_for_user())


@app.route("/knowledge-hub/group/comment/<int:comment_id>/delete", methods=["POST"])
@utils.login_required()
@utils.roles_required("Observer", "Operator", "Coordinator", "Admin")
def delete_group_notice_comment(comment_id):
    user_id = session["user_id"]
    role = session.get("role")
    is_admin = role == "Admin"

    comment = knowhub_repository.get_group_comment_by_id(comment_id)
    if not comment:
        flash("Comment not found.", "warning")
        return _knowledge_hub_redirect(_resolve_group_scope_for_user())

    is_author = comment["user_id"] == user_id
    can_moderate = is_admin or knowhub_repository.is_group_coordinator(user_id, comment["group_id"])

    if not is_author and not can_moderate:
        flash("You are not allowed to delete this comment.", "danger")
        return _knowledge_hub_redirect(_resolve_group_scope_for_user())

    deletion_reason = (request.form.get("deletion_reason") or "").strip()
    if not deletion_reason:
        flash("Please provide a reason before deleting the comment.", "warning")
        return _knowledge_hub_redirect(_resolve_group_scope_for_user())

    deleted = knowhub_repository.delete_group_notice_comment(comment_id, user_id, deletion_reason)
    if not deleted:
        flash("Comment could not be deleted.", "danger")
        return _knowledge_hub_redirect(_resolve_group_scope_for_user())

    flash("Comment deleted.", "success")
    next_url = request.form.get("next")
    if next_url:
        return redirect(next_url)
    return _knowledge_hub_redirect(_resolve_group_scope_for_user())


@app.route("/knowledge-hub/group/comment/<int:comment_id>/like", methods=["POST"])
@utils.login_required()
@utils.roles_required("Observer", "Operator", "Coordinator", "Admin")
def toggle_like_group_comment(comment_id):
    user_id = session["user_id"]
    role = session.get("role")
    is_admin = role == "Admin"

    comment = knowhub_repository.get_group_comment_by_id(comment_id)
    if not comment:
        flash("Comment not found.", "warning")
        return _knowledge_hub_redirect(_resolve_group_scope_for_user())

    if not is_admin and not knowhub_repository.is_active_group_member(user_id, comment["group_id"]):
        flash("You can only interact with comments in your group.", "danger")
        return _knowledge_hub_redirect(_resolve_group_scope_for_user())

    liked = knowhub_repository.toggle_group_comment_like(comment_id, user_id)
    flash("Comment liked." if liked else "Comment like removed.", "success")
    if liked:
        try:
            badge_repository.add_user_points(user_id, badge_repository.BadgeAction.LIKE, 'Liked comment')
        except Exception:
            pass
    next_url = request.form.get("next")
    if next_url:
        return redirect(next_url)
    return _knowledge_hub_redirect(_resolve_group_scope_for_user())
