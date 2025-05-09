
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, status, Response
from setezor.dependencies.project import role_required
from setezor.dependencies.uow_dependency import UOWDep
from setezor.managers import ProjectManager
from setezor.schemas.invite_link import InviteLinkCounter
from setezor.schemas.project import EnterTokenForm, ProjectCreateForm, ProjectPickForm, SearchVulnsSetTokenForm
from setezor.models import Project
from setezor.dependencies import get_current_project_for_ws, get_user_id, get_current_project
from setezor.services.auth_service import AuthService
from setezor.managers import WS_MANAGER
from setezor.schemas.roles import Roles
from setezor.services.scan_service import ScanService


router = APIRouter(
    prefix="/project",
    tags=["Project"],
)


@router.post("", status_code=201)
async def create_project(
    form: ProjectCreateForm,
    uow: UOWDep,
    response: Response,
    user_id: str = Depends(get_user_id)
) -> Project:
    new_project = await ProjectManager.create_project(uow=uow, name=form.name,
                                                      owner_id=user_id)
    last_scan = await ScanService.get_latest(uow=uow, project_id=new_project.id)
    token_pairs = await AuthService.set_current_scan(uow=uow,
                                                     project_id=new_project.id,
                                                     user_id=user_id,
                                                     scan_id=last_scan.id)
    if not token_pairs:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    response.set_cookie(key="access_token",
                        value=token_pairs.get("access_token"),
                        secure=True,
                        httponly=True)
    response.set_cookie(key="refresh_token",
                        value=token_pairs.get("refresh_token"),
                        secure=True,
                        httponly=True)
    return new_project

@router.post("/set_current", status_code=200)
async def set_current(
    uow: UOWDep,
    project: ProjectPickForm,
    response: Response,
    user_id: str = Depends(get_user_id)
) -> bool:
    last_scan = await ScanService.get_latest(uow=uow, project_id=project.project_id)
    token_pairs = await AuthService.set_current_scan(uow=uow,
                                                     project_id=project.project_id,
                                                     user_id=user_id,
                                                     scan_id=last_scan.id)
    if not token_pairs:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    response.set_cookie(key="access_token",
                        value=token_pairs.get("access_token"),
                        secure=True,
                        httponly=True)
    response.set_cookie(key="refresh_token",
                        value=token_pairs.get("refresh_token"),
                        secure=True,
                        httponly=True)
    return True


@router.delete("")
async def delete_project_by_id(
    uow: UOWDep,
    project: ProjectPickForm,
    user_id: str = Depends(get_user_id)
) -> bool:
    return await ProjectManager.delete_by_id(uow=uow,
                                             user_id=user_id,
                                             project_id=project.project_id)


@router.websocket("/ws")
async def websocket_handler(
    websocket: WebSocket,
    project_id: str = Depends(get_current_project_for_ws)
):
    await WS_MANAGER.connect(project_id=project_id, websocket=websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        WS_MANAGER.disconnect(project_id=project_id, websocket=websocket)


@router.put("/search_vulns_token")
async def set_search_vulns_token(
    uow: UOWDep,
    token_form: SearchVulnsSetTokenForm,
    project_id: str = Depends(get_current_project),
    _: bool = Depends(role_required([Roles.owner]))
):
    return await ProjectManager.set_search_vulns_token(uow=uow,
                                                       project_id=project_id,
                                                       token_form=token_form)


@router.post("/generate_invite_link")
async def generate_invite_link(
    uow: UOWDep,
    generate_link_form: InviteLinkCounter,
    project_id: str = Depends(get_current_project),
    _: bool = Depends(role_required([Roles.owner]))
):
    return await ProjectManager.generate_invite_link(uow=uow,
                                                     count_of_entries=generate_link_form.count,
                                                     project_id=project_id)


@router.post("/enter_by_token")
async def enter_by_invite_token(
    uow: UOWDep,
    enter_token_form: EnterTokenForm,
    response: Response,
    user_id: str = Depends(get_user_id),
):
    project_id = await ProjectManager.connect_new_user_to_project(uow=uow,
                                                                  user_id=user_id,
                                                                  enter_token_form=enter_token_form)
    last_scan = await ScanService.get_latest(uow=uow, project_id=project_id)
    token_pairs = await AuthService.set_current_scan(uow=uow,
                                                     project_id=project_id,
                                                     user_id=user_id,
                                                     scan_id=last_scan.id)
    if not token_pairs:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    response.set_cookie(key="access_token",
                        value=token_pairs.get("access_token"),
                        secure=True,
                        httponly=True)
    response.set_cookie(key="refresh_token",
                        value=token_pairs.get("refresh_token"),
                        secure=True,
                        httponly=True)
    return True