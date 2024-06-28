import datetime
import logging
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_prefix
import xacro

log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=log_level)

world_frame = 'world'
x = '-1.0'
y = '-1.0'
z = '0.0'

package_name = 'jetbot_sim'
base_xacro_file = 'my-jetbot.xacro'
install_dir = get_package_prefix(package_name)
robot_model_path = os.path.join(get_package_share_directory(package_name))
xacro_file = os.path.join(robot_model_path, 'xacro', base_xacro_file)


def set_gazebo_env_vars():
    # This is to find the models inside the models folder in my_box_bot_gazebo package
    gazebo_models_path = os.path.join(package_name, 'models')
    if 'GAZEBO_MODEL_PATH' in os.environ:
        os.environ['GAZEBO_MODEL_PATH'] = f'{os.environ["GAZEBO_MODEL_PATH"]}:{install_dir}/share:{gazebo_models_path}'
    else:
        os.environ['GAZEBO_MODEL_PATH'] = f'{install_dir}/share:{gazebo_models_path}'

    if 'GAZEBO_PLUGIN_PATH' in os.environ:
        os.environ['GAZEBO_PLUGIN_PATH'] = f'{os.environ["GAZEBO_PLUGIN_PATH"]}:{install_dir}/lib'
    else:
        os.environ['GAZEBO_PLUGIN_PATH'] = f'{install_dir}/lib'

    logging.debug(f'GAZEBO MODELS PATH=={str(os.environ["GAZEBO_MODEL_PATH"])}')
    logging.debug(f'GAZEBO PLUGINS PATH=={str(os.environ["GAZEBO_PLUGIN_PATH"])}')


def process_xacro_file():
    # convert XACRO file into URDF
    logging.debug("parsing xacro doc")
    doc = xacro.parse(open(xacro_file))
    xacro.process_doc(doc)

    # save for debugging
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    outfile_file = os.path.join("/tmp", f"{os.path.splitext(os.path.split(xacro_file)[-1])[0]}-{timestamp}.urdf")
    with open(outfile_file, 'w') as f:
        f.write(doc.toprettyxml(indent="    "))
    return doc.toxml()


def generate_robot_state_publisher_node():
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    return Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        parameters=[{'use_sim_time': use_sim_time, 'robot_description': process_xacro_file()}],
        output='screen'
    )


def generate_robot_spawn():
    robot_topic = 'robot_description'
    logging.debug(f'robot spawn topic is {robot_topic}')
    return Node(
        name='spawn_entity',
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-entity', 'jetbot', '-x', x, '-y', y, '-z', z, '-topic', robot_topic]
    )


def generate_static_transform_publisher_node():
    logging.debug('creating static transform')
    return Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_transform_publisher_odom',
        output='screen',
        emulate_tty=True,
        arguments=[x, y, z, '0', '0', '0', world_frame, 'odom']
    )


def generate_rviz_node():
    # RVIZ Configuration
    rviz_config_file = os.path.join(get_package_share_directory(package_name), 'rviz', 'config.rviz')
    print(f'rviz config dir: {rviz_config_file}')

    print('creating rviz2 node')
    return Node(
            package='rviz2',
            executable='rviz2',
            output='screen',
            name='rviz_node',
            parameters=[{'use_sim_time': True}],
            arguments=['-d', rviz_config_file])


def generate_gazebo_description():
    set_gazebo_env_vars()
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory('gazebo_ros'), 'launch'), '/gazebo.launch.py']),
        launch_arguments={"verbose": "false", 'pause': 'true'}.items(),
    )


def generate_launch_description():
    logging.debug('starting generate_launch_description')
    # joint_state_publisher = Node(
    #     package='joint_state_publisher',
    #     executable='joint_state_publisher',
    #     output='screen'
    # )

    return LaunchDescription([
        generate_robot_state_publisher_node(),
        generate_robot_spawn(),
        generate_static_transform_publisher_node(),
        generate_rviz_node(),
        generate_gazebo_description(),
    ])
