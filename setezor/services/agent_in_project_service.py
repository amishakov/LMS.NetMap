from random import randint
from typing import List

from fastapi import HTTPException
from setezor.managers.websocket_manager import WS_MANAGER
from setezor.models import Agent, Object, MAC, IP, Network, ASN, DNS_A, Domain
from setezor.models.agent_in_project import AgentInProject
from setezor.models.base import generate_unique_id
from setezor.schemas.task import WebSocketMessage
from setezor.tools.graph import find_all_paths
from setezor.unit_of_work import UnitOfWork
from setezor.schemas.agent import AgentAdd, AgentAddToProject, InterfaceOfAgent
from setezor.tools.ip_tools import get_network


class AgentInProjectService:
    @classmethod
    async def get_agent(cls, uow: UnitOfWork, agent_id_in_project: str, project_id: str):
        async with uow:
            return await uow.agent_in_project.find_one(id=agent_id_in_project,
                                                       project_id=project_id)

    @classmethod
    async def get_agent_in_project(cls, uow: UnitOfWork, id: str):
        async with uow:
            return await uow.agent_in_project.find_one(id=id)

    @classmethod
    def find_all_paths(cls, graph, start, end):
        def dfs(current, path, visited):
            path.append(current)
            visited.add(current)
            if current == end:
                paths.append(path.copy())
            else:
                for neighbor in graph.get(current, []):
                    if neighbor not in visited:
                        dfs(neighbor, path, visited)
            path.pop()
            visited.remove(current)
        paths = []
        dfs(start, [], set())
        for i in range(len(paths)):
            paths[i] = paths[i][1:]
        return paths


    @classmethod
    async def get_id_and_names_from_parents(cls, uow: UnitOfWork, project_id: str) -> dict:
        async with uow:
            users_in_project = await uow.user_project.list_project_users(project_id=project_id)
            server_agent_obj = await uow.agent.find_one(name="Server", secret_key="")
            server_agent_in_project = await uow.agent_in_project.find_one(agent_id=server_agent_obj.id, project_id=project_id)
            agents_for_graph = await uow.agent_in_project.all_agents(list_users = [user.id for user, role in users_in_project])
        graph = {}
        agent_p_agent = {}
        agents_in_project = set()
        for agent, agent_in_project, parent_agent, parent_agent_in_project in agents_for_graph:
            if agent.id not in agent_p_agent:
                graph[agent.id] = []
                agent_p_agent[agent.id] = []
                if agent_in_project and agent.id not in agents_in_project:
                    agents_in_project.add(agent.id)
            graph[agent.id].append(parent_agent.id)
            agent_p_agent[agent.id].append(
                {"parent_agent_id_in_project": agent_in_project.id if agent_in_project else None,
                 "parent_agent_name": agent.name}
            )
        result = {}
        uniq = {}
        for agent in agents_in_project:
            result[agent] = []
            uniq[agent] = set()
            for path in cls.find_all_paths(graph, agent, server_agent_obj.id):
                for id in path:
                    if id in agents_in_project:
                        for item in agent_p_agent[id]:
                            if item["parent_agent_id_in_project"] not in uniq[agent]:
                                uniq[agent].add(item["parent_agent_id_in_project"])
                                result[agent].append(item)
                                break
                        break
                    if id == server_agent_obj.id:
                        if server_agent_in_project.id not in uniq[agent]:
                            uniq[agent].add(server_agent_in_project.id)
                            result[agent].append(
                                {"parent_agent_id_in_project": server_agent_in_project.id,
                                "parent_agent_name": server_agent_obj.name})
                        break
        return result


    @classmethod
    async def get_agents_in_project(cls, uow: UnitOfWork, project_id: str) -> list:
        async with uow:
            agents_for_table = await uow.agent_in_project.list_for_table(project_id=project_id)

        parents = await cls.get_id_and_names_from_parents(uow = uow, project_id = project_id)

        result = []
        uniq_agents = set()
        for agent, agent_in_project, parent_agent, user in agents_for_table:
            if agent.id in uniq_agents:
                continue
            uniq_agents.add(agent.id)
            result.append({
                    "id": agent_in_project.id,
                    "name": agent.name,
                    "description": agent.description,
                    "color": agent_in_project.color,
                    "rest_url": agent.rest_url,
                    "parent_agent_id": parent_agent.id if parent_agent else None,
                    "parent_agent_name": ', '.join([item.get("parent_agent_name") for item in parents.get(agent.id, [])]),
                    "secret_key": agent.secret_key,
                    "user_name": user.login if user else '',
                    "object_id": agent_in_project.object_id
            })
        return result

    @classmethod
    async def get_agents_for_tasks(cls, uow: UnitOfWork, project_id: str) -> list:
        async with uow:
            server_agent = await uow.agent.find_one(name="Server", secret_key="")
            agents_for_tasks = await uow.agent_in_project.list_for_tasks(project_id=project_id)

        result = []
        uniq_agents = set([server_agent.id])
        for agent, agent_in_project in agents_for_tasks:
            if agent.id in uniq_agents:
                continue
            uniq_agents.add(agent.id)
            result.append({
                    "id": agent_in_project.id,
                    "name": agent.name,
                    "description": agent.description,
                    "color": agent_in_project.color,
                    "rest_url": agent.rest_url,
            })
        return result


    @classmethod
    async def possible_agents(cls, uow: UnitOfWork, user_id: str):
        async with uow:
            server_agent = await uow.agent.find_one(name="Server", secret_key="")
            res: list = await uow.agent.user_connected_agents(user_id=user_id)
            result = []
            for agent in res:
                if agent.id != server_agent.id:
                    result.append({
                        "id": agent.id,
                        "name": agent.name,
                        "description": agent.description,
                        "rest_url": agent.rest_url,
                    })
            return result
        
    @classmethod
    async def add_user_agents_to_project(cls, uow: UnitOfWork, agents: AgentAddToProject, user_id: str, project_id: str):
        async with uow:
            user_agents = await uow.agent.user_connected_agents(user_id=user_id)
            user_agents_ids = {agent.id for agent in user_agents}
        for agent_id in agents.agents:
            if not agent_id in user_agents_ids:
                raise HTTPException(status_code=400, detail="You are not allowed to connect agents, which are not yours")
        async with uow:
            for agent_id, to_connect in agents.agents.items():
                agent_in_project = await uow.agent_in_project.find_one(agent_id=agent_id, project_id=project_id)
                if not agent_in_project:
                    if to_connect:
                        obj_in_project_id, ag_in_project_id = generate_unique_id(), generate_unique_id()
                        new_agent_obj_model_in_project = Object(id=obj_in_project_id,
                                                                agent_id=ag_in_project_id,
                                                                project_id=project_id)

                        uow.object.add(new_agent_obj_model_in_project.model_dump())
                        new_agent_in_project = AgentInProject(
                            id=ag_in_project_id,
                            object_id=new_agent_obj_model_in_project.id,
                            color="#" + hex(randint(0, 16777215))[2:].zfill(6),
                            agent_id=agent_id,
                            project_id=project_id
                        )
                        uow.agent_in_project.add(new_agent_in_project.model_dump())
            await uow.commit()


    @classmethod
    async def get_interfaces(cls, uow: UnitOfWork, project_id: str, id: str):
        async with uow:
            agent = await uow.agent_in_project.find_one(id=id, project_id=project_id)
            macs = await uow.mac.get_interfaces(object_id=agent.object_id)
            return macs


    @classmethod
    async def save_interfaces(cls, uow: UnitOfWork, id: str, project_id: str, interfaces: List[InterfaceOfAgent]):
        async with uow:
            agent_in_project = await uow.agent_in_project.find_one(id=id, project_id=project_id)
            agent = await uow.agent.find_one(id=agent_in_project.agent_id)
            macs = await uow.mac.get_interfaces(object_id=agent_in_project.object_id)
            hashMap = set()
            for mac in macs:
                hashMap.add((mac.mac, mac.ip))
            for interface in interfaces:
                if (interface.mac, interface.ip) in hashMap:
                    continue
                new_asn = ASN(id=generate_unique_id(),
                              project_id=project_id)
                uow.asn.add(new_asn.model_dump())

                start_ip, broadcast = get_network(ip=interface.ip, mask=24)
                new_network = Network(id=generate_unique_id(),
                                      start_ip=start_ip,
                                      mask=24,
                                      project_id=project_id,
                                      asn_id=new_asn.id)
                uow.network.add(new_network.model_dump())

                new_mac = MAC(id=generate_unique_id(),
                              mac=interface.mac,
                              name=interface.name,
                              object_id=agent_in_project.object_id,
                              project_id=project_id)
                uow.mac.add(new_mac.model_dump())

                new_ip = IP(id=generate_unique_id(),
                            ip=interface.ip,
                            network_id=new_network.id,
                            mac_id=new_mac.id,
                            project_id=project_id)
                uow.ip.add(new_ip.model_dump())

                new_domain = Domain(id=generate_unique_id(),
                                    project_id=project_id)
                uow.domain.add(new_domain.model_dump())

                new_dns_a = DNS_A(target_domain_id=new_domain.id,
                                  target_ip_id=new_ip.id, project_id=project_id)
                uow.dns_a.add(new_dns_a.model_dump())

            await uow.commit()
            message = WebSocketMessage(
                title="Info", text=f"Saved interfaces for {agent.name}", type="info")
            await WS_MANAGER.send_message(project_id=project_id, message=message)
        return True


    @classmethod
    async def update_agent_color(cls, uow: UnitOfWork, project_id: str, agent_id:int, color: str):
        async with uow:
            agent_in_db = await uow.agent_in_project.find_one(id=agent_id, project_id=project_id)
            if not agent_in_db:
                return None
            agent = await uow.agent_in_project.edit_one(id=agent_id, data={"color": color})
            await uow.commit()
            return color
